#!/usr/bin/env python3
"""
Contract Extraction Script

Extracts comprehensive structured data from PDF contracts.
"""

if __name__ == '__main__':
    import sys
    import os

    # Add src to path for imports
    sys.path.insert(0, os.path.dirname(__file__))

    from src.extract import main
    main()
