"""
Enhanced Contract Extraction Script
Leverages the Responses API to generate structured data, including clause variables,
directly from contract text using a JSON-only response format.
"""

import argparse
import json
import os
import time
from pathlib import Path
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv
from openai import OpenAI
from openai._base_client import _DefaultHttpxClient, _DefaultAsyncHttpxClient
from pypdf import PdfReader

from .utils import extract_json_from_string, read_text_file, save_json_string_to_file

# Load environment variables from .env file
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise EnvironmentError("OPENAI_API_KEY is not set. Please configure your .env file.")


# Temporary patch: httpx 0.28 replaced the `proxies` keyword with `proxy`.
# OpenAI 1.40.0 still passes `proxies`, so we strip it before delegating
# to httpx to keep compatibility when proxy support is not used.
if not getattr(_DefaultHttpxClient, "_proxy_patch_applied", False):
    _orig_sync_init = _DefaultHttpxClient.__init__

    def _patched_sync_init(self, **kwargs):
        proxies = kwargs.pop("proxies", None)
        if proxies is not None:
            kwargs["proxy"] = proxies
        return _orig_sync_init(self, **kwargs)

    _DefaultHttpxClient.__init__ = _patched_sync_init
    _DefaultHttpxClient._proxy_patch_applied = True

if not getattr(_DefaultAsyncHttpxClient, "_proxy_patch_applied", False):
    _orig_async_init = _DefaultAsyncHttpxClient.__init__

    def _patched_async_init(self, **kwargs):
        proxies = kwargs.pop("proxies", None)
        if proxies is not None:
            kwargs["proxy"] = proxies
        return _orig_async_init(self, **kwargs)

    _DefaultAsyncHttpxClient.__init__ = _patched_async_init
    _DefaultAsyncHttpxClient._proxy_patch_applied = True

client = OpenAI(
    api_key=OPENAI_API_KEY,
    timeout=60.0,
    max_retries=3,
)

SUPPORTS_RESPONSE_FORMAT = True

ROOT_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT_DIR / "prompts"
DEFAULT_MAX_CONTRACT_CHARS = 120_000


def resolve_path(env_key: str, default_path: Path) -> Path:
    """Resolve a path from an environment override or fall back to the provided default."""
    override = os.getenv(env_key)
    if override:
        candidate = Path(override)
        if not candidate.is_absolute():
            candidate = ROOT_DIR / candidate
        return candidate
    return default_path


def load_text_file(path: Path) -> str:
    """Load a text file and raise a useful error if missing."""
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return read_text_file(str(path))


def get_system_instruction() -> str:
    """Load the system instruction prompt."""
    system_path = resolve_path("EXTRACT_SYSTEM_PROMPT_PATH", PROMPTS_DIR / "system_prompt.txt")
    return load_text_file(system_path)


def get_extraction_prompt(prompt_path_override: Optional[Path] = None) -> str:
    """Select the extraction prompt, preferring enhanced prompts when available."""
    if prompt_path_override is not None:
        return load_text_file(prompt_path_override)

    prompt_override_env = os.getenv("EXTRACT_PROMPT_PATH")
    if prompt_override_env:
        override_path = Path(prompt_override_env)
        if not override_path.is_absolute():
            override_path = ROOT_DIR / override_path
        if override_path.exists():
            return load_text_file(override_path)

    candidate_paths: List[Path] = [
        PROMPTS_DIR / "enhanced_extraction_prompt.txt",
        PROMPTS_DIR / "extraction_prompt.txt",
    ]
    for path in candidate_paths:
        if path.exists():
            return load_text_file(path)

    raise FileNotFoundError(
        "No extraction prompt available. Add prompts/enhanced_extraction_prompt.txt "
        "or prompts/extraction_prompt.txt, or set EXTRACT_PROMPT_PATH."
    )


def load_contract_text(pdf_path: Path) -> str:
    """Extract textual content from a PDF contract."""
    reader = PdfReader(str(pdf_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    contract_text = "\n\n".join(pages).strip()
    if not contract_text:
        raise ValueError(f"No extractable text found in {pdf_path}")
    return contract_text


def enforce_length_budget(contract_text: str, source_name: str) -> None:
    """Abort early if the contract exceeds the configured character budget."""
    max_chars_env = os.getenv("EXTRACT_MAX_CHARS")
    try:
        max_chars = int(max_chars_env) if max_chars_env else DEFAULT_MAX_CONTRACT_CHARS
    except ValueError:
        max_chars = DEFAULT_MAX_CONTRACT_CHARS

    if len(contract_text) > max_chars:
        raise ValueError(
            f"Contract '{source_name}' is {len(contract_text):,} characters, exceeding the limit of "
            f"{max_chars:,}. Split the document or raise EXTRACT_MAX_CHARS cautiously."
        )


def call_responses_api(contract_text: str, extraction_prompt: str, system_instruction: Optional[str] = None) -> str:
    """Call the OpenAI Responses API with basic retry logic."""
    global SUPPORTS_RESPONSE_FORMAT  # noqa: PLW0603
    messages: List[Dict[str, str]] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    user_content = (
        extraction_prompt.strip()
        + "\n\n=== INPUT CONTRACT TEXT START ===\n"
        + contract_text
        + "\n=== INPUT CONTRACT TEXT END ==="
    )
    messages.append({"role": "user", "content": user_content})

    last_error: Optional[Exception] = None
    for attempt in range(1, 4):
        try:
            kwargs: Dict[str, Any] = {}
            if SUPPORTS_RESPONSE_FORMAT:
                kwargs["response_format"] = {"type": "json_object"}

            resp = client.responses.create(
                model=os.getenv("EXTRACT_MODEL", "gpt-4o-mini"),
                input=messages,
                temperature=0,
                max_output_tokens=20000,
                **kwargs,
            )
            return resp.output_text
        except TypeError as exc:
            if SUPPORTS_RESPONSE_FORMAT and "response_format" in str(exc):
                print("  ⚠ OpenAI client does not support response_format; falling back to prompt-enforced JSON.")
                globals()["SUPPORTS_RESPONSE_FORMAT"] = False
                continue
            last_error = exc
            break
        except Exception as exc:  # pylint: disable=broad-except
            last_error = exc
            if attempt == 3:
                break
            time.sleep(2 * attempt)
    raise last_error or RuntimeError("Failed to call Responses API")


def normalize_contract_json(raw: Dict[str, Any], source_name: str) -> Dict[str, Any]:
    """Adapt the raw model response into the schema expected by loaders."""
    data = dict(raw)  # shallow copy
    agreement: Dict[str, Any] = dict(data.get("agreement") or {})

    # Normalize naming.
    if "contract_type" in agreement and "agreement_type" not in agreement:
        agreement["agreement_type"] = agreement.pop("contract_type")
    if "auto_renew" in agreement and "auto_renewal" not in agreement:
        agreement["auto_renewal"] = agreement.pop("auto_renew")

    # Promote parties.
    parties = data.pop("parties", []) or agreement.get("parties")
    normalized_parties = []
    for party in parties or []:
        normalized_parties.append(
            {
                "role": party.get("role"),
                "name": party.get("legal_name") or party.get("name"),
                "incorporation_country": party.get("country"),
                "incorporation_state": party.get("state"),
            }
        )
    if normalized_parties:
        agreement["parties"] = normalized_parties

    # Split governing law / dispute resolution.
    gl = data.pop("governing_law_and_dispute_resolution", {}) or {}
    if gl:
        agreement["governing_law"] = {
            "country": gl.get("governing_country"),
            "state": gl.get("governing_state"),
            "most_favored_country": gl.get("most_favored_country"),
        }
        agreement["dispute_resolution"] = {
            "method": gl.get("dispute_resolution_method"),
            "venue": gl.get("venue"),
            "jurisdiction": gl.get("jurisdiction"),
            "governing_rules": gl.get("rules_governing_dispute_resolution"),
        }

    data["agreement"] = agreement

    # Ensure clauses array exists.
    clauses = data.get("clauses")
    if clauses is None:
        data["clauses"] = []

    # Record filename for downstream IDs.
    data.setdefault("file_name", source_name)

    # Ensure a stable contract identifier flows downstream.
    contract_id = (
        data.get("contract_id")
        or agreement.get("contract_id")
        or Path(source_name).stem
    )
    data["contract_id"] = contract_id
    agreement.setdefault("contract_id", contract_id)

    return data


def validate_enhanced_json(json_data):
    """
    Validate that the extracted JSON contains enhanced fields.

    Args:
        json_data: Parsed JSON dictionary

    Returns:
        Dictionary with validation results
    """
    validation = {
        "valid": True,
        "warnings": [],
        "info": {},
    }

    agreement = json_data.get("agreement", {})

    # Check for enhanced fields
    if "liability_cap" in agreement:
        validation["info"]["has_liability_cap"] = agreement["liability_cap"].get("exists", False)

    if "obligations" in agreement and agreement["obligations"]:
        validation["info"]["obligation_count"] = len(agreement["obligations"])
    else:
        validation["warnings"].append("No obligations extracted")

    if "compliance_frameworks" in agreement and agreement["compliance_frameworks"]:
        validation["info"]["compliance_frameworks"] = [
            cf["framework_name"] for cf in agreement["compliance_frameworks"]
        ]

    if "intellectual_property" in agreement and agreement["intellectual_property"]:
        validation["info"]["ip_provision_count"] = len(agreement["intellectual_property"])

    # Check for missing critical fields
    if not agreement.get("parties"):
        validation["warnings"].append("No parties extracted")
        validation["valid"] = False

    if not agreement.get("governing_law"):
        validation["warnings"].append("No governing law extracted")

    return validation


def main(
    single_input: Optional[Path] = None,
    prompt_override: Optional[Path] = None,
    single_output: Optional[Path] = None,
):
    """Main extraction loop."""
    if single_input is not None:
        single_input = Path(single_input).expanduser().resolve()
    if prompt_override is not None:
        prompt_override = Path(prompt_override).expanduser().resolve()
    if single_output is not None:
        single_output = Path(single_output).expanduser().resolve()

    input_folder = resolve_path("EXTRACT_INPUT_DIR", ROOT_DIR / "data" / "input")
    output_folder = resolve_path("EXTRACT_OUTPUT_DIR", ROOT_DIR / "data" / "output")
    debug_folder = resolve_path("EXTRACT_DEBUG_DIR", ROOT_DIR / "data" / "debug")

    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(debug_folder, exist_ok=True)

    if single_output is not None:
        single_output.parent.mkdir(parents=True, exist_ok=True)

    system_instruction = get_system_instruction()
    extraction_prompt = get_extraction_prompt(prompt_override)

    if single_input is not None:
        pdf_path = single_input
        if not pdf_path.exists():
            raise FileNotFoundError(f"Input file not found: {pdf_path}")
        pdf_files = [pdf_path]
        input_descriptor = str(pdf_path)
    else:
        if not input_folder.exists():
            raise FileNotFoundError(f"Input folder not found: {input_folder}")
        pdf_files = sorted([path for path in input_folder.iterdir() if path.suffix.lower() == ".pdf"])
        if not pdf_files:
            print(f"No PDF files found in {input_folder}")
            return
        input_descriptor = str(input_folder)

    if single_output is not None and len(pdf_files) > 1:
        raise ValueError("--out can only be used for single-file extraction.")

    print(f"Found {len(pdf_files)} PDF files to process from {input_descriptor}")
    print("=" * 80)

    successful = 0
    failed = 0

    for idx, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{idx}/{len(pdf_files)}] Processing: {pdf_path.name}")
        print("-" * 80)

        try:
            contract_text = load_contract_text(pdf_path)
            enforce_length_budget(contract_text, pdf_path.name)
            complete_response = call_responses_api(contract_text, extraction_prompt, system_instruction)

            debug_file = debug_folder / f"complete_response_{pdf_path.name}.json"
            save_json_string_to_file(complete_response, debug_file)
            print(f"  ✓ Raw response saved to: {debug_file}")

            contract_json = extract_json_from_string(complete_response)

            if contract_json:
                contract_json = normalize_contract_json(contract_json, pdf_path.name)
                validation = validate_enhanced_json(contract_json)

                if single_output is not None:
                    output_file = single_output
                else:
                    output_file = output_folder / f"{pdf_path.name}.json"
                save_json_string_to_file(json.dumps(contract_json, indent=2), output_file)
                print(f"  ✓ Structured JSON saved to: {output_file}")

                if validation["info"]:
                    print("  ✓ Validation info:")
                    for key, value in validation["info"].items():
                        print(f"    - {key}: {value}")

                if validation["warnings"]:
                    print("  ⚠ Warnings:")
                    for warning in validation["warnings"]:
                        print(f"    - {warning}")

                successful += 1
            else:
                print("  ✗ Failed to extract valid JSON")
                failed += 1

        except json.JSONDecodeError as e:
            print(f"  ✗ JSON decode error: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ Error processing file: {e}")
            failed += 1

    print("\n" + "=" * 80)
    print(f"Total files: {len(pdf_files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run contract extraction.")
    parser.add_argument(
        "--input",
        type=str,
        help="Path to a single PDF contract.",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Override extraction prompt path.",
    )
    parser.add_argument(
        "--out",
        type=str,
        help="Write result JSON to this path (single-file mode).",
    )
    args = parser.parse_args()

    single_input_path = Path(args.input).expanduser().resolve() if args.input else None
    prompt_override_path = Path(args.prompt).expanduser().resolve() if args.prompt else None
    single_output_path = Path(args.out).expanduser().resolve() if args.out else None

    main(
        single_input=single_input_path,
        prompt_override=prompt_override_path,
        single_output=single_output_path,
    )
