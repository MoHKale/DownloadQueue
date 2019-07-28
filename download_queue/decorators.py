import typing, functools, time

ROEArgument = typing.Union[typing.Tuple[str, int], int]  # ('', 5) or 5

def repeat_on_error(repeat_count: ROEArgument, wait_on_failure: ROEArgument):
    """runs a function and if an erorr is encountered, waits some interval
    and then reruns the function upto repeat_count times. If on the last
    attempt an error is again encountered, the function allows the exception
    to capture control flow.

    NOTE this decorator is exclusively for the use of `download_queue.Downloader`

    Parameters
    ----------
    repeat_count
        how many times the function should be invoked. The argument can be
        given as a numerical value, in which case that's how many times the
        function will be tried. It can also be given as a collection, in which
        case the 0th index will be the attribute in self which will be taken
        to find the repeat_count. The second attribute will be a fallback
        value to be used when self doesn't have the attribute.
    wait_on_failure
        how long to wait after an exception has been encountered and before
        the next download attempt. this argument is parsed in the same way
        as repeat_count.
    """
    parse_roe_arg = lambda X: (None, X) if isinstance(X, int) else X

    def extract_attr(self, identifier, default, *args):
        # extract identifier from self if identifier was given & self has identifier as an attribute
        return getattr(self, identifier) if identifier and hasattr(self, identifier) else default

    def decorator(func):
        _attempt_count = parse_roe_arg(repeat_count)
        _attempt_delay = parse_roe_arg(wait_on_failure)

        @functools.wraps(func)
        def wrapped(self, *args, **kwargs):
            attempt_count = max(extract_attr(self, *_attempt_count), 1)
            attempt_delay = max(extract_attr(self, *_attempt_delay), 0)

            def recursively_invoke_func(attempt):
                """recursively invokes the argument to this decorator
                such that, if the worst should happen and every download
                attempt failed, the resulting stacktrace will include every
                error encountered on every attempt.

                TODO This may not be the desired behaviour, consider adding
                     an optional flag allowing a person to invoke the function
                     non recursively.
                NOTE this approach is verbose enough that raising a single
                     exception expresses more than enough information about
                     the request.
                """
                try:
                    return func(self, *args, **kwargs)
                except KeyboardInterrupt: raise
                except:  # pylint: disable=E722
                    if attempt <= 0:
                        self.logger.exception('failed to download after %03d attempts using %s with args: %s' % (
                            attempt_count, self.__class__.__name__, repr(self.serialise_args())[1:-1]
                        ))

                        raise
                    else:
                        time.sleep(attempt_delay)  # wait interval
                        return recursively_invoke_func(attempt-1)

            return recursively_invoke_func(attempt_count-1)
        return wrapped
    return decorator
