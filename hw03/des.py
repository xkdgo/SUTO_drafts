class Test(Structure):
    test = CharField("test", nullable=False, required=True)
    tset = CharField("tset", nullable=False, required=True)
    email = EmailField("email", nullable=False, required=False)
