# Contributing to SimBricks

We are very happy that you would like to contribute to SimBricks.

The following is a set of guidelines for contributing to the whole SimBricks
project, which is hosted in the
[SimBricks Organization](https://github.com/simbricks) on GitHub. These are
mostly guidelines, not rules. Use your best judgment, and feel free to propose
changes to this document in a pull request.

# Code of Conduct

This project and everyone participating in it is governed by the
[SimBricks Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are
expected to uphold this code.

# Getting Help

If you have a question about the project, technical or organizational, you can
get in touch with us, either through
[GitHub Discussions](https://github.com/simbricks/simbricks/discussions) or our
[Slack workspace](https://join.slack.com/t/simbricks/shared_invite/zt-16y96155y-xspnVcm18EUkbUHDcSVonA).


# How Can I Contribute?

## Reporting Bugs

An excellent way to get started on contributing to SimBricks is to report any
problems you run into, small or large. Please report bugs through
[GitHub Issues](https://github.com/simbricks/simbricks/issues)

When you are creating a bug report, please include as many details as possible,
to help us resolve issues faster. Also be sure to monitor your notifications for
follow-up questions from our side, and let us know if we have fixed your
problem.

## Discuss Your Use-Cases With Us

We are interested in how you would like to use SimBricks. If you are trying to
determine what modifications are required to use SimBricks for your use-case,
we are happy to discuss this with you, either through the discussion board or
Slack.

## Suggesting Enhancements

If you have concrete suggestions for Enhancements you are welcome to file a
GitHub issue, especially if you are planning on potentially addressing them
yourself down the line (the latter is not a requirement). Should you have less
concrete ideas or suggestions, the "Ideas" discussion board is the right place
to get a discussion going to flesh things out.

## Pull Requests

Once you are ready to start writing code, fork the repository and start working
on your feature branch. Once done, submit a pull request (please refer to any
related issues in the description) to the SimBricks repository, and we will work
with you to adopt your changes where possible. Please make sure that pull
requests are logical units, and do not mix unrelated commits in one pull
request.

If you are looking for a place to get started, we have tagged a few issues as
[good first issues](https://github.com/simbricks/simbricks/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).

## More Complex Contributions

For larger or more intrusive changes to SimBricks we would suggest you discuss
your plan with us first, so we can coordinate changes and make sure we will also
be able to adopt your changes down the road. This can hopefully also help avoid
duplicate effort. These discussions can happen in issues or the discussion
board or in Slack if you would like to iterate more quickly. Where a public
discussion of what you are planning is a problem, please contact us to discuss
things privately.

# Style Guides

Please read through our style guides before preparing your contributions to
avoid unnecessary effort later to reformat code etc. before we can push it to
the repository.

## Git Commits

Git commits in the SimBricks repo should be small (easy to review)
self-contained logical units. Each commit should only change one thing. For
example,
do not mix semantic changes with reformatting of surrounding code, or bug fixes
with performance optimizations.

### History

We expect a clean git history where each commit compiles and (with few
exceptions) passes the linter checks. We also do not push merge commits, so
please make sure to use `git pull --rebase`, `git rebase`, etc.

### Message Format

Commit messages must start with a short (less than 75 character) summary line
that starts with the subsystem name, followed by a colon and space. For
subsystem names, refer to the git log, particularly for related files. Separate
this with a blank line from the complete description. Here is an example:

```
lib/simbricks/base: add SimBricksBaseIfEstablish()

SimBricksBaseIfEstablish handles parallel connections and handshakes on
multiple SimBricks connections.
```

If your commit fixes or is otherwise related to a GitHub issue, please refer to
it in the commit message.

## Markdown and Text Files

Just as with the rest of the source code, text and markdown files should not
exceed line lengths of 80 characters (with exceptions for URLs and other things
that cannot be wrapped easily).

## C / C++

We require that all our C/C++ code adhere to the
[Google C++ Style Guide](https://google.github.io/styleguide/cppguide.html).
Note that some legacy code may still have violations, but any new changes
should still adhere to the style guide.

## Python

We require that all our Python code adheres to the [Google Python Style
Guide](https://google.github.io/styleguide/pyguide.html). Note that some legacy
code may still have violations, but any new changes should still adhere to the
style guide.


# Attribution
These contribution baselines are partially adapted from
[Atom](https://github.com/atom/atom/blob/master/CONTRIBUTING.md).