def scrsplit(a, n):
    k, m = divmod(len(a), n)
    lst = (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))
    return [x for x in lst if x]
