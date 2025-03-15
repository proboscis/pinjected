
# Update Logs
- 0.2.115: Updated documentation structures.
- 0.2.40: Added support for overriding default design with 'with' statement:
```python

run_train: Injected = train()

with design(
        val_loader=one_sample_val_loader,
        train_loader=one_sample_train_loader,
        training_loop_tasks=Injected.list()
):
    test_training: Injected = training_test() # here, test_training will use the overridden providers! 
    with design(
        batch_size=1
    ):
        do_anything:Injected = task_with_batch_size_1() # you can even nest the 'with' statement!

```

