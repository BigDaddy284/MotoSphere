"""The data store: the pipeline's own database, an SQLite file.

Collected records, their sources, their history and the review queue live
here. Published files are written from it by the export step; nothing reads
it during a visit to the site.
"""
