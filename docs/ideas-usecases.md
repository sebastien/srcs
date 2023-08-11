# Use Cases

## Main and side quests

A developer start to work off the main branch, and is focusing on
implementing one main feature. Along the way, they find that make a few
changes to the documentation, add discover a bug that they fix by
creating a test case and resolving the problem.

In this scenario we can see the following:

- A developer is focused on a main line of work (main quest)
- They may encounter things to do that are not directly related to the
  main line of work (side quests).

This can be solved by marking changes as part of one or other tasks. Fo
instance

    $ srcs record # Records on the main task
    $ srcs record BugFix
