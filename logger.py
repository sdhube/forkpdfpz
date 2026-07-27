import logging

fmt = "%(module)-20s:%(lineno)4d %(funcName)-25s %(levelname)-5s:%(message)s"
logging.basicConfig(level=logging.INFO, format=fmt)
logger = logging.getLogger(__name__)
