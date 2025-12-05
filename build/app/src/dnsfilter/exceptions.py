class BlueCatError(Exception):
    """Basic class for all exceptions."""
    pass

class BlueCatEnvError(BlueCatError):
    """Error related to fetching env variables process."""
    pass

class BlueCatLoginError(BlueCatError):
    """Error related to Bluecat Authentication."""
    pass

class BlueCatAPIError(BlueCatError):
    """Error related to API calls."""
    pass

class BlueCatNotFoundError(BlueCatError):
    """Error related to not found ressources."""
    pass

class BindError(Exception):
    """Base class for all BIND-related exceptions."""
    pass

class BindEnvError(BindError):
    """Error related to BIND environment variables."""
    pass

class BindRPZError(BindError):
    """Error related to RPZ file generation."""
    pass

class BindConnectionError(BindError):
    """Error related to BIND server connection."""
    pass



class CoreError(Exception):
    """Base class for all core-related exceptions."""
    pass

class AWSError(CoreError):
    """Error related to AWS operations."""
    pass

class ConfigError(CoreError):
    """Error related to configuration operations."""
    pass