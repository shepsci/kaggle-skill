# Benchmarks

Use this module for Kaggle benchmark task workflows and benchmark-related MCP
endpoint notes.

## Common Commands

```bash
kaggle b init -y
kaggle b t push my-task -f task.py --wait 600
kaggle b t run my-task -m gemini-2.5-pro --wait
kaggle b t status my-task
kaggle b t download my-task --include-source
```

Benchmark lifecycle commands can create resources and consume quota. Confirm
the task name, model, visibility, and expected cost before running them.

## References

- [benchmarks-cli.md](references/benchmarks-cli.md)
- [benchmark-endpoints.md](references/benchmark-endpoints.md)
