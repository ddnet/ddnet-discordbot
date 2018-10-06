function adjustName() {
    const namediv = document.getElementById("name");
    while (namediv.clientWidth > 700) {
        const style = window.getComputedStyle(namediv, null).getPropertyValue("font-size");
        const fontSize = parseFloat(style);
        namediv.style.fontSize = fontSize - 1 + "px";
    }
}

/* 2 rows = 160 */
function adjustTiles() {
    const tilesDiv = document.getElementById("tiles");
    const tiles = document.getElementsByClassName('tile');
    while (tilesDiv.offsetHeight > 160) {
        for (let i = 0; i < tiles.length; ++i) {
            const tile = tiles[i];
            tile.style.width = tile.offsetWidth - 1 + 'px';
        }
    }
}

/* 1 = 29, 2 = 58, 3 = 87 */
function adjustTeamRank() {
    const element = document.getElementById("team-rank");
    if (typeof(element) !== 'undefined' && element != null) {
        let style = window.getComputedStyle(element, null).getPropertyValue("font-size");
        let fontSize = parseFloat(style);
        if (element.offsetHeight === 58) {
            style = window.getComputedStyle(element, null).getPropertyValue("font-size");
            fontSize = parseFloat(style);
            while (element.offsetHeight >= 29 && fontSize >= 22) {
                style = window.getComputedStyle(element, null).getPropertyValue("font-size");
                fontSize = parseFloat(style);
                element.style.fontSize = fontSize - 1 + "px";
            }
        } else if (element.offsetHeight === 87) {
            style = window.getComputedStyle(element, null).getPropertyValue("font-size");
            fontSize = parseFloat(style);
            while (element.offsetHeight >= 58 && fontSize >= 20) {
                style = window.getComputedStyle(element, null).getPropertyValue("font-size");
                fontSize = parseFloat(style);
                element.style.fontSize = fontSize - 1 + "px";
            }
        } else {
            while (element.offsetHeight > 87) {
                style = window.getComputedStyle(element, null).getPropertyValue("font-size");
                fontSize = parseFloat(style);
                element.style.fontSize = fontSize - 1 + "px";
            }
        }
    }
    removeExtraRows();
}

function getOffset(el) {
    const rect = el.getBoundingClientRect();
    return {
        left: rect.left + window.scrollX,
        top: rect.top + window.scrollY
    };
}

function removeExtraRows() {
    const table = document.getElementById("ranks-table");
    for (let i = 0, row; row = table.rows[i]; i++) {
        console.log(getOffset(row).top);
        const rect = row.getBoundingClientRect();
        console.log(rect.top + document.documentElement.scrollTop);
        if (rect.top > 441) {
            row.style.display = 'none';
        }
    }
}

window.onload = function () {
    adjustTiles();
    adjustName();
    adjustTeamRank();
};

window.onerror = (event) => {
    event.preventDefault()
};
