#!/usr/bin/env python3
"""
Generate database schema DDL from SQLAlchemy models.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine, MetaData
from sqlalchemy.schema import CreateTable

# Import all models to register them
from app.models.user import User
from app.models.note import Note
from app.models.upload import Upload
from app.models.analysis import Analysis

def generate_schema():
    # Create a dummy engine for DDL generation
    engine = create_engine("postgresql://dummy:dummy@localhost/dummy")

    # Create metadata
    metadata = MetaData()

    # Get all tables from the models
    tables = [User.__table__, Note.__table__, Upload.__table__, Analysis.__table__]

    # Generate DDL
    ddl_statements = []
    for table in tables:
        ddl = str(CreateTable(table).compile(engine))
        ddl_statements.append(ddl)

    return "\n\n".join(ddl_statements)

if __name__ == "__main__":
    schema = generate_schema()
    print(schema)