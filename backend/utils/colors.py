class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def error(message):
        print(f"{Colors.FAIL}{message}{Colors.ENDC}")

    @staticmethod
    def ok(message):
        print(f"{Colors.OKCYAN}{message}{Colors.ENDC}")

    @staticmethod
    def success(message):
        print(f"{Colors.OKGREEN}{message}{Colors.ENDC}")

    @staticmethod
    def warning(message):
        print(f"{Colors.WARNING}{message}{Colors.ENDC}")

    @staticmethod
    def bold(message):
        print(f"{Colors.BOLD}{message}{Colors.ENDC}")

    @staticmethod
    def underline(message):
        print(f"{Colors.UNDERLINE}{message}{Colors.ENDC}")

    @staticmethod
    def header(message):
        print(f"{Colors.HEADER}{message}{Colors.ENDC}")

    @staticmethod
    def info(message):
        print(f"{Colors.OKCYAN}{message}{Colors.ENDC}")