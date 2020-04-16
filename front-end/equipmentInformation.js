evrythng.setup({apiUrl: 'https://api.evrythng.com', geolocation: false});

const app = new evrythng.TrustedApplication(apiKey);

function queryStrToDict(searchStr) {

    function fn(query) {
        const idx = {};
        for (let i = query.length - 1; i >= 0; i--)
            idx[query[i]] = i;
        const queryDict = {};
        if ('&' in idx) {
            let queryParams = fn(query.slice(idx['&'] + 1, query.length));
            for (let k in queryParams)
                queryDict[k] = queryParams[k];
            query = query.slice(0, idx['&']);
        }
        queryDict[query.slice(0, idx['='])] = query.slice(idx['='] + 1, idx['&']);
        return queryDict;
    }

    return fn(searchStr.slice(1, searchStr.length))

}


function queryParam(param) {
    if (this.queryParams === undefined)
        this.queryParams = queryStrToDict(window.location.search)
    return this.queryParams[param]
}


async function updateCollection(collectionId, dict) {
    for (let k in dict) {
        let label = document.createElement('div');
        label.textContent = k;
        label.setAttribute('class', 'col');

        let value = document.createElement('div');
        value.setAttribute('class', 'col');

        value.textContent = dict[k];
        let identifierEntry = document.createElement('div');
        identifierEntry.setAttribute('class', 'row');

        identifierEntry.appendChild(label);
        identifierEntry.appendChild(value);
        document.getElementById(collectionId).appendChild(identifierEntry);
    }
    document.getElementById(collectionId).hasChildNodes() && document.getElementById(collectionId + "Card").removeAttribute("hidden")
}


function updateInUseView(inUse) {
    if (inUse) {
        document.getElementById("equipmentState").classList.add('btn-success');
        document.getElementById("equipmentState").classList.replace('btn-success', 'btn-danger');
        document.getElementById("equipmentState").innerText = "Occupied";
    } else {
        document.getElementById("equipmentState").classList.add('btn-danger');
        document.getElementById("equipmentState").classList.replace('btn-danger', 'btn-success');
        document.getElementById("equipmentState").innerText = "Free";
    }
}




document.getElementById("equipmentState").onclick = async () => {
    const thng = await app.thng(queryParam('thngId')).read();
    let inUse = !thng.properties.inuse;
    const action = {
        type: inUse ? '_InUse' : '_Free',
        thng: thng.id
    };

    updateInUseView(inUse);
    if (inUse)
        await app.thng(thng.id).action(action.type).create(action).then();
    else
        await app.thng(thng.id).action(action.type).create(action).then();
};

alert(window.query)
document.addEventListener("DOMContentLoaded", async () => {
    if (apiKey === undefined) {
        $('#equipmentTitle').text('Query string missing');
    }
    const thng = await app.thng(queryParam('thngId')).read();
    localStorage.setItem("thng", JSON.stringify(thng));
    updateInUseView(thng.properties.inuse);
    const product = await app.product(thng.product).read().then();
    $('#brandValue').text('product.brand');
    await updateCollection('thngIdentifiers', thng.identifiers);
    await updateCollection('thngCustomFields', thng.customFields);
    const productInformation = {
        brand: product.brand,
        'product name': product.name,
        specification: product.description
    };
    await updateCollection('productInformation', productInformation);
    const currentLocation = await app.place(thng.location.place).read();
    // JSON.stringify(currentLocation)
    const placeInformation = {};
    placeInformation.name = currentLocation.name;
    for (let k in currentLocation.customFields)
        placeInformation[k.replace('_', ' ')] = currentLocation.customFields[k];

    await updateCollection('locationInformation', placeInformation);
    window.addEventListener('blur', onFocusOut);
    window.addEventListener('focus', onFocus);

}, false);

function onFocusOut() {
    window.addEventListener('focusin', onFocus);
    window.removeEventListener('focusout', onFocusOut, false);
}

async function onFocus() {
    const thng = await app.thng(queryParam('thngId')).read();
    updateInUseView(thng.properties.inuse);
    $('#locationInformation').empty();
    const currentLocation = await app.place(thng.location.place).read();

    const placeInformation = {};
    placeInformation.name = currentLocation.name;
    for (let k in currentLocation.customFields)
        placeInformation[k.replace('_', ' ')] = currentLocation.customFields[k];

    await updateCollection('locationInformation', placeInformation);
    window.addEventListener('focusout', onFocusOut);
    window.removeEventListener('focusin', onFocus, false);
}