#!/usr/bin/env python3
"""
Direct pgvector Ingestion - 360 Documents
Creates embeddings and inserts directly into pgvector database.
"""

import json
import os
import sys
import time
import uuid
from pathlib import Path

import psycopg2
import requests
import yaml
from pgvector.psycopg2 import register_vector

# Expanded to 360 documents across 20 categories (18 per category)
DOCUMENTS = [
    # This will be too long for a single command. Let me break it up.
]
