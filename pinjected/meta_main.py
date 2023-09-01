from pinjected.ide_supports.create_configs import run_with_meta_context

if __name__ == '__main__':
    """
    An entrypoint for running a injected with __meta_design__ integrated.
    This is used to create IDE configurations, and other metadata related tasks.
    """
    import fire
    fire.Fire(run_with_meta_context)
