adjustName = function () {
    var namediv = document.getElementById("name");
    while (namediv.clientWidth > 700) {
        var style = window.getComputedStyle(namediv , null).getPropertyValue("font-size");
        var fontSize = parseFloat(style);
        namediv.style.fontSize = fontSize - 1 + "px";
    }
};


/* 2 rows = 160 */
function  adjustTiles() {
    var tilesDiv = document.getElementById("tiles");
    var tiles = document.getElementsByClassName('tile');
    while (tilesDiv.offsetHeight > 160) {
        for (var i = 0; i < tiles.length; ++i) {
            var tile = tiles[i];
            tile.style.width = tile.offsetWidth - 1 + 'px';
        }
    };
};

/* 1 = 29, 2 = 58, 3 = 87 */
function adjustTeamRank() {
    var element = document.getElementById("team-rank");
    if (typeof(element) != 'undefined' && element != null) {
        originalHeight = element.offsetHeight;
        var style = window.getComputedStyle(element, null).getPropertyValue("font-size");
        var fontSize = parseFloat(style);
        originalFontSize = fontSize;
        if (element.offsetHeight == 58) {
            var style = window.getComputedStyle(element, null).getPropertyValue("font-size");
            var fontSize = parseFloat(style);
            while (element.offsetHeight >= 29 && fontSize >= 22) {
                var style = window.getComputedStyle(element, null).getPropertyValue("font-size");
                var fontSize = parseFloat(style);
                element.style.fontSize = fontSize - 1 + "px";
            }
        } else if (element.offsetHeight == 87) {
            var style = window.getComputedStyle(element, null).getPropertyValue("font-size");
            var fontSize = parseFloat(style);
            while (element.offsetHeight >= 58 && fontSize >= 20) {
                var style = window.getComputedStyle(element, null).getPropertyValue("font-size");
                var fontSize = parseFloat(style);
                element.style.fontSize = fontSize - 1 + "px";
            }
        } else {
            while (element.offsetHeight > 87) {
                var style = window.getComputedStyle(element, null).getPropertyValue("font-size");
                var fontSize = parseFloat(style);
                element.style.fontSize = fontSize - 1 + "px";
            }
        };
    };
    removeExtraRows();
};

function getOffset(el) {
    const rect = el.getBoundingClientRect();
    return {
      left: rect.left + window.scrollX,
      top: rect.top + window.scrollY
    };
  }


function removeExtraRows() {
    var table = document.getElementById("ranks-table");
    for (var i = 0, row; row = table.rows[i]; i++) {
        console.log(getOffset(row).top);
        var rect = row.getBoundingClientRect();
        console.log(rect.top + document.documentElement.scrollTop);
        if (rect.top > 441) {
            row.style.display = 'none';
        };
    }
};

function stoperror() {
    return true;
 }

window.onload = function(event) {
    adjustTiles();
    adjustName();
    adjustTeamRank();
};

window.onerror = stoperror();