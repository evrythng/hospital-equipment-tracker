async function thngLocationName(thngId) {
    const placeId = (await app.thng(thngId).read()).location.place;
    return (await app.place(placeId).read()).name
}

async function eventActionLocationName(event) {
    const placeId = event.action.customFields.place;
    return (await app.place(placeId).read()).name
}

async function updateThngTagsShortOverview(thngId) {
    const thng = await app.thng(thngId).read();
    const placeId = thng.location.place;
    const placeName = (await app.place(placeId).read()).name;
    const tags = [thng.properties.inuse ? "inuse" : "free", placeName];
    return await app.thng(thngId).update({tags: tags});
}

// @filter(onActionCreated) action.type=_TransferEquipment
async function onActionCreated(event) {
    try {
        const thngId = event.action.thng;

        const fromLocation = await thngLocationName(thngId);
        const toLocation = await eventActionLocationName(event);
        if (fromLocation!==undefined && toLocation!==undefined)
            await app.thng(thngId).property().update({transfer: `${fromLocation}->${toLocation}`});
        await app.thng(thngId).location().update([{place: event.action.customFields.place}]);
        await updateThngTagsShortOverview(thngId);
    } catch (e) {
        logger.error(e.message || e.errors[0]);
    }
    done();
}