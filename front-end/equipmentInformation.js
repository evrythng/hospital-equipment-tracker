
evrythng.setup({apiUrl: 'https://api.evrythng.com', geolocation: false});




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


const apiKey = queryParam('apiKey');

const app = new evrythng.TrustedApplication(apiKey);


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
    const uiInfo = {
        true:{
            equipmentState:'OCCUPIED',
            equipmentStateButton: 'Change Status to Free'
        },
        false: {
            equipmentState:'FREE',
            equipmentStateButton: 'Change Status to Occupied'
        }
    };
    for (let k in uiInfo[inUse])
        $(`#${k}`).text(uiInfo[inUse][k]);
}




$("#equipmentStateButton").click( async () => {

    const thng = await app.thng(queryParam('thngId')).read();
    let inUse = !thng.properties.inuse;
    updateInUseView(inUse)

    const action = {
        type: inUse ? '_InUse' : '_Free',
        thng: thng.id
    };


    if (inUse)
        await app.thng(thng.id).action(action.type).create(action).then();
    else
        await app.thng(thng.id).action(action.type).create(action).then();
});

function updateTable(tableId, values) {
    $(`#${tableId}`).empty();
    for (let k in values)
        $(`#${tableId}`).append(`<tr><td>${k.replace('_', ' ')}</td><td>${values[k]}</td>`);
}

$( window ).on( "load", async () => {
    if (apiKey === undefined) {
        $('#equipmentTitle').text('Query string missing');
    }
    const thng = await app.thng(queryParam('thngId')).read();

    localStorage.setItem("thng", JSON.stringify(thng));
    const product = await app.product(thng.product).read().then();


    const productInformation = {
        brand: product.brand,
        'name': product.name,
        specification: product.description
    };

    updateTable('productTable', productInformation);
    const currentLocation = await app.place(thng.location.place).read();
    const locationValues = currentLocation.customFields;
    locationValues['name'] = currentLocation.name;
    updateTable('locationTable', locationValues);

    $(window).focus(onFocus);
    $(window).focusout(onFocusOut);

});

function onFocusOut() {
    $(window).focus(onFocus);
    $(window).off('focusout');
}

async function onFocus() {
    const thng = await app.thng(queryParam('thngId')).read();
    let inUse = !thng.properties.inuse;
    updateInUseView(inUse);
    // updateInUseView(thng.properties.inuse);


    const currentLocation = await app.place(thng.location.place).read();

    const locationValues = currentLocation.customFields;
    locationValues['name'] = currentLocation.name;
    updateTable('locationTable', locationValues);
    $(window).off('focus');
    $(window).focusout(onFocusOut);
}
// https://covid.evrythng.io/equipmentinformation.html?thngId=U8kF7pW2HhePA7wcV7N9Essp