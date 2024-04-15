"""
Failure of exporter v1.
- The structure got too complex
- Let's clarify the requirement for exporting an Injected.

What we need, is a list of CodeBlocks.
For an injected to be exportable, it needs to be convertable to CodeBlocks.

Some functionalities of injected do violate the requirement of being exportable.
For example, call to a map function with local lambda easily violates the requirement.

"""
