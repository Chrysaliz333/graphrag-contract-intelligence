#!/usr/bin/env python3
"""
Knowledge Graph Creation Script

Creates Neo4j knowledge graph from extracted contract JSON files.
"""

if __name__ == '__main__':
    import sys
    import os

    # Add src to path for imports
    sys.path.insert(0, os.path.dirname(__file__))

    from src.create_graph import main
    main()
