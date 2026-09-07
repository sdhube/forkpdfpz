
| Folder | Responsibility | Architecture concept |
|---|---|---|
| `domain/` | Book, asset, manifest, collection, value objects | DDD Domain / Clean Entities |
| `application/` | Import, sanitize, scan, validate, organize workflows | Clean Use Cases / Application Services |
| `metadata/` | PDF metadata extraction, normalization, scanning | Domain Support / Adapter Boundary |
| `processing/` | Sanitation, renaming, merging, PDF manipulation | Domain-specific Processing |
| `storage/` | Database, YAML, filesystem persistence | Infrastructure |
| `importers/` | Copy/import PDFs into managed storage | Application + Infrastructure |
| `adapters/` | External libraries, legacy interfaces, external systems | Hexagonal Adapters |
| `utils/` | Generic technical utilities such as logging | Shared Infrastructure |
| `cli/` | Command-line interface | Interface Adapter |
| `tests/` | Fakes and test-only helpers | Testing Support |