# Prototype Entrypoint

The runnable prototype is exposed at `codebase/app.py` to match the hackathon
submission structure. The canonical application source remains at the project
root so paths to the local, gitignored lecture artifacts stay consistent.

Run from the repository root:

```bash
streamlit run codebase/app.py --server.port 8501
```

The same application can also be started directly with `streamlit run app.py`.
