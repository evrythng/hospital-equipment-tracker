
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
localStorage.setItem("apiKey", apiKey);
const app = new evrythng.TrustedApplication(apiKey);


async function readUsedAndUnusedEquipment() {
  const equipment = [];
  const iterator = app.thng().setPerPage(100).pages();

  let page;
  while (!(page = await iterator.next()).done) {
    equipment.push(...page.value);
  }
  const equipmentStats = {true:0, false:0};
  for (let e of equipment)
      equipmentStats[e.properties.inuse]++;
  return {'equipmentFreeValue': equipmentStats[false], 'equipmentInUseValue': equipmentStats[true]};
}


$( window ).on( "load", async () => {

    if (apiKey === undefined) {
        alert('api key is missing. please set the trusted app api key as ?apiKey=')
    }
    const equipmentStats = await readUsedAndUnusedEquipment();
    for (let k in equipmentStats)
        $(`#${k}`).text(equipmentStats[k]);

    $(window).focus(onFocus);
    $(window).focusout(onFocusOut);

});

function onFocusOut() {
    $(window).focus(onFocus);
    $(window).off('focusout');
}

async function onFocus() {
    const equipmentStats = await readUsedAndUnusedEquipment();
    for (let k in equipmentStats)
        $(`#${k}`).text(equipmentStats[k]);
    $(window).off('focus');
    $(window).focusout(onFocusOut);
}
