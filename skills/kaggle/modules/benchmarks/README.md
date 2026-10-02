# Benchmarks

Kaggle Benchmarks task commands and the benchmark MCP tools.

```bash
kaggle benchmarks init --yes
kaggle benchmarks tasks push my-task -f task.py --wait
kaggle benchmarks tasks run my-task -m gemini-2.5-pro --wait
kaggle benchmarks tasks status my-task
kaggle benchmarks tasks download my-task --include-source
```

`kaggle b` and `kaggle b t` are the short forms.

Pushing and running tasks creates resources on the account and uses model
quota. Confirm the task name, the models, and the expected cost with the user
first.

For writing tasks, use Kaggle's own skills: `write-kaggle-benchmarks` in
https://github.com/Kaggle/kaggle-skills and the `kaggle-benchmarks` skill in
https://github.com/Kaggle/kaggle-benchmarks.

## References

- [benchmarks-cli.md](references/benchmarks-cli.md)
- [benchmark-endpoints.md](references/benchmark-endpoints.md)
