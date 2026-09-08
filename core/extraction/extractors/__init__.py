"""
Extraction modules for domain documents.
"""

from core.extraction.extractors.base import BaseExtractor
from core.extraction.extractors.payslip import PayslipExtractor
from core.extraction.extractors.bank_statement import BankStatementExtractor
from core.extraction.extractors.tax_return import TaxReturnExtractor
from core.extraction.extractors.id_card import IdCardExtractor

__all__ = [
    "BaseExtractor",
    "PayslipExtractor",
    "BankStatementExtractor",
    "TaxReturnExtractor",
    "IdCardExtractor",
]
