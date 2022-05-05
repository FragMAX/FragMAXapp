class IDs
{
    constructor()
    {
        this.nextId = 0;
        this.objToId = new Map();
    }

    getId(obj)
    {
        if (this.objToId.has(obj))
        {
            return this.objToId.get(obj);
        }

        const objId = this.nextId++;
        this.objToId.set(obj, objId);

        return objId;
    }
}

function wrapWithIds(items)
{
    let entries = [];
    for (const item of items)
    {
        entries.push({id: ids.getId(item), item: item});
    }
    return entries;
}
