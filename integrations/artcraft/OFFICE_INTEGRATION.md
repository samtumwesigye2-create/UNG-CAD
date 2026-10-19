# UNG Office document bridge (macOS)

The script `ung-office-open-mac.sh` routes local documents to an installed ArtCraft app, with Microsoft Office as a fallback when installed. It never edits or converts files itself.

```bash
bash integrations/artcraft/ung-office-open-mac.sh "$HOME/Documents/example.docx"
bash integrations/artcraft/ung-office-open-mac.sh "$HOME/Documents/budget.xlsx"
bash integrations/artcraft/ung-office-open-mac.sh "$HOME/Documents/presentation.pptx"
```

Routing: WordCraft → Microsoft Word for DOC/DOCX/ODT; GridCraft → Microsoft Excel for XLS/XLSX/ODS; DeckCraft → Microsoft PowerPoint for PPT/PPTX/ODP; PdfCraft → Preview for PDF.

**Compatibility gate:** launch success does not mean the app can correctly parse, render, edit or round-trip the document. Back up originals and verify each format using representative files, formulas, embedded assets and layout before using this bridge for production. Microsoft apps are not installed by this script. This is a local adapter, not a browser service or an Office API integration.
