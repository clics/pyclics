# Changelog

## Version 2.0

Plugin architecture (see `pyclics.plugin`) allowing
- pluggable cluster algorithms
- pluggable CLICS form creation

This results in a change to the CLI, replacing the subcommands
`subgraph` and `communities` with the `cluster` subcommand,
taking the name of a cluster algorithm as first argument,
where the communities detection algorithm used for CLICS² is
available as `infomap` clusterer.
