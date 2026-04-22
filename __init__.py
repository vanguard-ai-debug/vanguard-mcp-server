#!/usr/bin/env python3
"""
AegisRAG MCP Server Package

A Model Context Protocol server that provides access to the AegisRAG knowledge management API.
"""

__version__ = "1.0.0"
__author__ = "AegisRAG Team"
__description__ = "AegisRAG MCP Server - Model Context Protocol server for AegisRAG API"

from weknora_mcp_server import AegisRAGClient, run

__all__ = ["AegisRAGClient", "run"]
