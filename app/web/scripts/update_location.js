const evrythng = EVT;
evrythng.setup({apiUrl: 'https://api.evrythng.com'});
evrythng.use(evrythng.Scan);
const app = new evrythng.TrustedApp(apiKey);
const UI = {
    buttonStartCamera: document.getElementById('button-start-camera'),
    checkboxRedirect: document.getElementById('checkbox-redirect'),
    anchorResult: document.getElementById('result'),
    selectMethod: document.getElementById('select-type')
};


const getQueryParam = (key) => {
    const params = window.location.search.substring(1)
        .split('&')
        .reduce((res, item) => {
            const [key, value] = item.split('=');
            res[key] = value;
            return res;
        }, {});

    return params[key];
};

const createFilter = () => {
    const map = {
        qr: {method: '2d', type: 'qr_code'},
        ir: {method: 'ir', type: 'image'},
        other: {method: 'auto', type: 'auto'},
    };
    return map['qr'];
};

const startCamera = () => {


    app.scanStream({
        filter: createFilter(),
        containerId: 'stream_container',
    }).then((res) => {
        if (!res.length) {
            UI.anchorResult.innerHTML = 'No results';
            return;
        }

        // Raw URL
        const url = new URL((res.length && res[0].results.length)
            ? res[0].results[0].redirections[0]
            : res[0].meta.value.trim());

        UI.anchorResult.innerHTML = url;
        UI.anchorResult.href = url;
        const thng = JSON.parse(localStorage.thng);
        return app.place(pathToDict(url.pathname)['place']).read().then(place => {
            const action_type = '_TransferEquipment';
            const actionDocument = {
                "type": action_type,
                "thng": thng.id,
                "locationSource": "place",
                "customFields": {"place":place.id}
            };
            return app.action(action_type).create(actionDocument).then(data => {
                alert(`New location:  ${thng.name}`);
                history.go(-1);
            });
        });

    })
        .catch(console.log);
};

function pathToDict(path) {
    if (path[0] === '/') {
        path = path.slice(1, path.length);
    }
    if (path[path.lenth - 1] === '/')
        path = path.slice(0, path.length - 1);

    function keys(path) {
        const idx = {};
        for (let i = path.length - 1; i >= 0; i--)
            idx[path[i]] = i;
        const {value, collection} = values(path.slice(idx['/'] + 1, path.length));
        collection[path.slice(0, idx['/'])] = value;
        return collection
    }

    function values(path) {

        const idx = {};
        for (let i = path.length - 1; i >= 0; i--)
            idx[path[i]] = i;
        if (!('/' in idx))
            return {value: path, collection: {}};
        return {value: path.slice(0, idx['/']), collection: keys(path.slice(idx['/'] + 1, path.length))}
    }

    return keys(path)
}

document.addEventListener("DOMContentLoaded", async () => {
    if (apiKey === undefined) {
        $('#equipmentTitle').text('Query string missing');
    }
    const thng = JSON.parse(localStorage.thng);
    $('#equipmentTitle').text(thng.name);
    startCamera();
});