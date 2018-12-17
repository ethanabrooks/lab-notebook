# first party
import runs


class Logger:
    exists = False

    def __init__(self, quiet):
        # TODO: make this class singleton somehow
        # if Logger.exists:
        #     raise RuntimeError(
        #         "There should only be one logger in existence at a time.")
        Logger.exists = True
        self.quiet = quiet

    def print(self, *msg, **kwargs):
        if not self.quiet:
            print(*msg, **kwargs)

    def exit(self, *msg, **kwargs):
        self.print(*msg, **kwargs)
        exit()

    def exit_no_match(self, db, pattern):
        self.exit(f'No runs match pattern "{pattern}". Recorded runs:\n'
                  f'{runs.commands.ls.string(db)}')


class UI(Logger):
    def __init__(self, assume_yes: bool, quiet):
        super().__init__(quiet=quiet)
        self.assume_yes = assume_yes

    def get_permission(self, *question, sep):
        if self.assume_yes:
            return True
        question = sep.join(map(str, question)).rstrip(sep) + sep
        response = input(question)
        while True:
            response = response.lower()
            if response in ['y', 'yes']:
                return True
            if response in ['n', 'no']:
                return False
            else:
                response = input('Please enter y[es]|n[o]')

    def check_permission(self, *question, sep='\n'):
        if not self.get_permission(*question, "Continue?", sep=sep):
            self.exit()
