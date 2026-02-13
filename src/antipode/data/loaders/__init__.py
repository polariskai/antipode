"""
Data Loaders for Adversarial AML System

Provides interfaces for loading and storing scenario data
in various backends (PostgreSQL, Neo4j, file system).
"""

from .postgres_loader import PostgreSQLLoader
from .bank_loader import BankSchemaLoader

__all__ = ["PostgreSQLLoader", "BankSchemaLoader"]
