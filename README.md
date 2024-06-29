


# Pinjected
Welcome to Pinjected, a powerful dependency injection and dependency resolver library for Python inspired by pinject.

```bash
pip install pinjected
```

# Table of Contents

- [Introduction](docs_md/01_introduction.md)
- [Design](docs_md/02_design.md)
- [Decorators](docs_md/03_decorators.md)
- [Injected](docs_md/04_injected.md)
- [Running](docs_md/05_running.md)
- [Async Support](docs_md/06_async_support.md)
- [Resolver](docs_md/07_resolver.md)
- [Miscellaneous](docs_md/08_misc.md)
- [Appendix](docs_md/09_appendix.md)
- [Updates](docs_md/10_updates.md)
## [Introduction](docs_md/01_introduction.md)
Pinjected makes it easy to compose multiple Python objects to create a final object. It automatically creates dependencies and composes them, providing a clean and modular approach to dependency management. To learn more about the motivation behind Pinjected and its key concepts, check out the Introduction.
Design

## [Design](docs_md/02_design.md)
The Design section covers the core concept of Pinjected. It explains how to define a collection of objects and their dependencies using the Design class. You'll learn about binding instances, providers, and classes to create a dependency graph.

## [Decorators](docs_md/03_decorators.md)
Pinjected provides two decorators, @instance and @injected, to define provider functions. The Decorators section explains the differences between these decorators and how to use them effectively in your code.

## [Injected](docs_md/04_injected.md)
In the Injected section, you'll learn about the Injected class, which represents a variable that requires injection. This section covers how to create Injected instances, compose them, and use them as providers in your dependency graph.

## [Running](docs_md/05_running.md)
Pinjected supports running Injected instances from the command line and integrating with IDEs like IntelliJ IDEA. The Running section provides details on how to use the CLI and set up IDE integration for a smooth development experience.

## [Async Support](docs_md/06_async_support.md)
Pinjected offers support for asynchronous programming, allowing you to use async functions as providers. The Async Support section explains how to define and use async providers, as well as how to compose async Injected instances.

## [Resolver](docs_md/07_resolver.md)
The Resolver section dives into the object graph and resolver concepts in Pinjected. You'll learn how the resolver manages the lifecycle of injected variables and how to use it to retrieve instances from the dependency graph.

## [Miscellaneous](docs_md/08_misc.md)
For additional information, refer to the Miscellaneous section, which covers topics like performance considerations, comparisons with other DI libraries, and troubleshooting.

## [Appendix](docs_md/09_appendix.md)
The Appendix contains supplementary information, such as a comparison with pinject and other relevant details.

## [Updates](docs_md/10_updates.md)
Stay up to date with the latest changes and releases by checking the Updates section, which includes a changelog and migration guides.
We hope you find Pinjected helpful in your projects! If you have any questions or feedback, please don't hesitate to reach out.