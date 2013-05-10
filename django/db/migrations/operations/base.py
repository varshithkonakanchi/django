class Operation(object):
    """
    Base class for migration operations.

    It's responsible for both mutating the in-memory model state
    (see db/migrations/state.py) to represent what it performs, as well
    as actually performing it against a live database.

    Note that some operations won't modify memory state at all (e.g. data
    copying operations), and some will need their modifications to be
    optionally specified by the user (e.g. custom Python code snippets)
    """

    # If this migration can be run in reverse.
    # Some operations are impossible to reverse, like deleting data.
    reversible = True

    def state_forwards(self, app, state):
        """
        Takes the state from the previous migration, and mutates it
        so that it matches what this migration would perform.
        """
        raise NotImplementedError()

    def database_forwards(self, app, schema_editor, from_state, to_state):
        """
        Performs the mutation on the database schema in the normal
        (forwards) direction.
        """
        raise NotImplementedError()

    def database_backwards(self, app, schema_editor, from_state, to_state):
        """
        Performs the mutation on the database schema in the reverse
        direction - e.g. if this were CreateModel, it would in fact
        drop the model's table.
        """
        raise NotImplementedError()
