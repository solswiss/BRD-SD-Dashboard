import pysd

MODEL_FILEPATH = None # e.g. 'models/SEIQR_linked.mdl'

pysd.read_vensim(MODEL_FILEPATH) # will output a python version of the model translated by pysd
