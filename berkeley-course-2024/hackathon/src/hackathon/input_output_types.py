from typing import Dict, List
import numpy as np
from pydantic import BaseModel


class NamedEntities(BaseModel):
    named_entities: List[str]

class DocumentStructure(BaseModel):
    id: int
    text: str
    named_entities: NamedEntities
    triples: List[List[str]]
    
class DocumentStructures(BaseModel):    
    document_structures: List[DocumentStructure]
