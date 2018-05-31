from functools import wraps


class Logger:
    exists = False

    @staticmethod
    def wrapper(func):
        @wraps(func)
        def _wrapper(quiet, *args, **kwargs):
            return func(*args, **kwargs, logger=Logger(quiet=quiet))

        return _wrapper

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

    def exit_no_match(self, pattern):
        self.exit(f'No runs match pattern "{pattern}". Recorded runs:\n')
        # TODO
        # f'{tree_string(table["%"])}')


class UI(Logger):
    @staticmethod
    def wrapper(func):
        @wraps(func)
        def ui_wrapper(assume_yes, quiet, *args, **kwargs):
            return func(*args, **kwargs, logger=UI(assume_yes=assume_yes, quiet=quiet))

        return ui_wrapper

    def __init__(self, assume_yes: bool, quiet):
        super().__init__(quiet=quiet)
        self.assume_yes = assume_yes

    def get_permission(self, *question):
        if self.assume_yes:
            return True
        question = ' '.join(question)
        if not question.endswith((' ', '\n')):
            question += ' '
        response = input(question)
        while True:
            response = response.lower()
            if response in ['y', 'yes']:
                return True
            if response in ['n', 'no']:
                return False
            else:
                response = input('Please enter y[es]|n[o]')

    def check_permission(self, *question):
        if not self.get_permission(*question):
            self.exit()
