from tkinter import *

class Application(Frame):
  labelText = None
  label = None

  def __init__(self, master=Tk(), callback=None):
    master.title("Prospect Searcher")
    master.iconbitmap("./media/Prospect Searcher.ico")
    Frame.__init__(self, master)
    self.pack()
    self.msgLabel = StringVar()
    self.msgLabel.set("")
    self.createWidgets(callback=callback)

  def createWidgets(self, callback):
    Label(self, text="Search Google with:").grid(row=0, sticky=E)

    searchInput = Entry(self)
    searchInput.grid(row=0, column=1, columnspan=4)

    Label(self, text="Number of results to get:").grid(row=1, sticky=E)

    resultsInput = Entry(self)
    resultsInput.grid(row=1, column=1, columnspan=4)

    getSocials = StringVar()
    getSocials.set("False")

    Label(self, text="Get socials?").grid(row=2, sticky=E)

    trueSocials = Radiobutton(self, text="Yes", variable=getSocials, value="True")
    falseSocials = Radiobutton(self, text="No", variable=getSocials, value="False")
    trueSocials.grid(row=2, column=1, columnspan=2)
    falseSocials.grid(row=2, column=3, columnspan=2)

    reqTimeframe = StringVar()
    reqTimeframe.set("anytime")

    Label(self, text="Timeframe? In the past...").grid(row=3, sticky=E)

    dayRadio = Radiobutton(self, text="Day", variable=reqTimeframe, value="d")
    weekRadio = Radiobutton(self, text="Week", variable=reqTimeframe, value="w")
    monthRadio = Radiobutton(self, text="Month", variable=reqTimeframe, value="m")
    noneRadio = Radiobutton(self, text="Anytime", variable=reqTimeframe, value="anytime")
    dayRadio.grid(row=3, column=1)
    weekRadio.grid(row=3, column=2)
    monthRadio.grid(row=3, column=3)
    noneRadio.grid(row=3, column=4)

    reqSave = StringVar()
    reqSave.set(2)

    Label(self, text="Where to save?").grid(row=4, sticky=E)

    googleRadio = Radiobutton(self, text="Google Sheet", variable=reqSave, value=2)
    excelRadio = Radiobutton(self, text="Excel Sheet", variable=reqSave, value=1)
    googleRadio.grid(row=4, column=1, columnspan=2)
    excelRadio.grid(row=4, column=3, columnspan=2)

    submitButton = Button(self, text="Run", width=50, bg="lightgreen", command=lambda: callback(reqSearchString=searchInput.get(),\
        reqSocials=getSocials.get(), reqResults=resultsInput.get(), reqTimeframe=reqTimeframe.get(), reqSave=reqSave.get()))
    submitButton.grid(row=5, column=0, columnspan=5, padx=10, pady=10)

    msgLabel = Label(self, textvariable=self.msgLabel)
    self.label = msgLabel
    msgLabel.grid(row=6, column=0, columnspan=5, pady=0)

  def changeLabel(self, text, success):
    self.msgLabel.set("Message: " + str(text))
    if (success == True):
      self.label.config(fg="green")
    elif (success == False):
      self.label.config(fg="red")
    else:
      raise AttributeError