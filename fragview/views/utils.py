def open_txt(filename):
    """
    utility wrapper to open a text file with utf-8 encoding
    """
    return open(filename, "r", encoding="utf-8")


def scrsplit(a, n):
    k, m = divmod(len(a), n)
    lst = (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))
    return [x for x in lst if x]


def Filter(datasetsList, filtersList):
    return [str for str in datasetsList if any(sub in str for sub in filtersList)]
