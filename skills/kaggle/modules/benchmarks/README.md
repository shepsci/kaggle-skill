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

Run them through the skill, with the words after `kaggle` placed after `--`:

```bash
python3 scripts/kaggle_skill.py cli -- benchmarks tasks status my-task
python3 scripts/kaggle_skill.py cli --yes -- benchmarks tasks run my-task -m gemini-2.5-pro --wait
```

Pushing and running tasks creates resources on the account and uses model
quota. `tasks push`, `tasks run`, `tasks publish` and `tasks delete` are dry
runs until `--yes` comes before the `--`. Confirm the task name, the models,
and the expected cost with the user first.

For writing tasks, use Kaggle's own skills: `write-kaggle-benchmarks` in
https://github.com/Kaggle/kaggle-skills and the `kaggle-benchmarks` skill in
https://github.com/Kaggle/kaggle-benchmarks.

## References

- [benchmarks-cli.md](references/benchmarks-cli.md)
- [benchmark-endpoints.md](references/benchmark-endpoints.md)
