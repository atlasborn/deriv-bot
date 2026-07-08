class Models:
    def __init__(self, model_path = None):
        self.model_path = model_path
        self.model = None

    def load(self):
        self.model = keras.load_model(self.model_path)
