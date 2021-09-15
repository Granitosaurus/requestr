def domain_from_url(url: str):
    """gets domain from url sometimes"""
    return str(url).split("://", 1)[-1].split("/")[0]