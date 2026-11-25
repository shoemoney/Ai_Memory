# Fetching the separately licensed inputs

The book's benchmarks use third-party datasets whose terms are non-commercial, share-alike or otherwise not ours to redistribute. They are not in this repository. `download-inputs.py` fetches the originals from their upstream sources and records URL and digest manifests.

```sh
python3 release/download-inputs.py conversation --rebuild-samples
python3 release/download-inputs.py retrieval
python3 release/download-inputs.py prompt
```

Downloads go into `downloaded-inputs/` and keep their original terms; do not redistribute them. Source revisions are pinned except the upstream ArguAna archive URL, whose fetched digest is recorded.

Historical model traces, contextual prefixes, manually audited references and adapted prompt implementations are not hosted upstream, so downloading the inputs cannot restore those exact files. Rerunning needs the original protocol, runtime and models and may produce different bytes. The manual reference audit for the v2 extraction set has to be repeated.

`artifact-checksums.sha256` records the SHA-256 of the built book files in `build/`; run `sha256sum -c release/artifact-checksums.sha256` from the repository root.

Licences: code is MIT (`LICENSE`), text is CC BY 4.0 (`LICENSE-TEXT`); third-party notices are in `NOTICE` and `LICENSES/`.

The research under `benchmarks/inkling/` ships its summaries and raw traces where they are small and free of identifiers. Traces of 5 MB or more, and the regenerable training corpus, are not included and are available on request.
