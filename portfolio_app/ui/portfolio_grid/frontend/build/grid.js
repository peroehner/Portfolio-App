(function () {
  "use strict";

  function sendToStreamlit(type, payload) {
    window.parent.postMessage(
      Object.assign({ isStreamlitMessage: true, type: type }, payload),
      "*"
    );
  }

  function setFrameHeight(height) {
    sendToStreamlit("streamlit:setFrameHeight", { height: height });
  }

  function setComponentValue(value) {
    sendToStreamlit("streamlit:setComponentValue", {
      value: value,
      dataType: "json",
    });
  }

  var gridApi = null;
  var anchorIndex = null;
  var selectedRows = new Set();
  var rowData = [];
  var suppressEmit = false;
  var lastRowsJson = "";
  var lastColumnsJson = "";

  function rowsToSymbols(indices) {
    return indices
      .map(function (idx) {
        var row = rowData[idx];
        return row && row.Symbol != null ? String(row.Symbol) : "";
      })
      .filter(function (sym) {
        return sym.length > 0;
      });
  }

  function dataRowIndex(node) {
    if (!node || !node.data) return null;
    if (node.data.__rowIndex != null) return parseInt(node.data.__rowIndex, 10);
    return node.rowIndex;
  }

  function updateSelectedRowsFromPython(selected) {
    selectedRows = new Set(
      (selected || [])
        .map(function (r) {
          return parseInt(r, 10);
        })
        .filter(function (r) {
          return !isNaN(r);
        })
    );
    if (selectedRows.size === 1) {
      anchorIndex = Array.from(selectedRows)[0];
    } else if (selectedRows.size === 0) {
      anchorIndex = null;
    }
  }

  function applySelection(api) {
    if (!api) return;
    api.deselectAll();
    api.forEachNode(function (node) {
      var idx = dataRowIndex(node);
      if (idx == null) return;
      if (selectedRows.has(idx)) {
        node.setSelected(true);
      }
    });
  }

  function emitSelection() {
    if (suppressEmit) return;
    var rows = Array.from(selectedRows).sort(function (a, b) {
      return a - b;
    });
    setComponentValue({ rows: rows, symbols: rowsToSymbols(rows) });
  }

  function computeNextSelection(idx, event) {
    var shift = !!(event && event.shiftKey);
    var toggle = !!(
      event &&
      (event.ctrlKey || event.metaKey || event.altKey)
    );
    var next = new Set(selectedRows);

    if (shift && anchorIndex !== null) {
      next = new Set();
      var start = Math.min(anchorIndex, idx);
      var end = Math.max(anchorIndex, idx);
      for (var i = start; i <= end; i++) {
        next.add(i);
      }
      return next;
    }

    if (toggle) {
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    }

    anchorIndex = idx;
    return new Set([idx]);
  }

  function onRowClicked(params) {
    if (!params || !params.node) return;
    var idx = dataRowIndex(params.node);
    if (idx == null) return;
    selectedRows = computeNextSelection(idx, params.event);
    applySelection(params.api);
    emitSelection();
  }

  function destroyGrid() {
    if (gridApi && gridApi.destroy) {
      gridApi.destroy();
    }
    gridApi = null;
    lastRowsJson = "";
    lastColumnsJson = "";
  }

  function createGrid(root, columnDefs) {
    var options = {
      columnDefs: columnDefs,
      rowData: rowData,
      defaultColDef: {
        sortable: false,
        resizable: true,
        filter: false,
        minWidth: 72,
      },
      rowSelection: "multiple",
      suppressRowClickSelection: true,
      suppressCellFocus: true,
      animateRows: false,
      headerHeight: 34,
      rowHeight: 32,
      domLayout: "normal",
      getRowId: function (params) {
        return String(
          params.data.__rowIndex != null ? params.data.__rowIndex : params.node.rowIndex
        );
      },
      onRowClicked: onRowClicked,
      onGridReady: function (params) {
        applySelection(params.api);
      },
    };

    gridApi = agGrid.createGrid(root, options);
  }

  function renderGrid(args) {
    var root = document.getElementById("grid-root");
    if (!root) return;

    rowData = Array.isArray(args.rows) ? args.rows : [];
    var height = parseInt(args.height, 10) || 320;
    setFrameHeight(height);

    var columnDefs = Array.isArray(args.column_defs) ? args.column_defs : [];
    updateSelectedRowsFromPython(args.selected_rows);

    var rowsJson = JSON.stringify(rowData);
    var columnsJson = JSON.stringify(columnDefs);

    if (gridApi && columnsJson === lastColumnsJson) {
      if (rowsJson !== lastRowsJson) {
        gridApi.setGridOption("rowData", rowData);
        lastRowsJson = rowsJson;
      }
      applySelection(gridApi);
      return;
    }

    destroyGrid();
    root.innerHTML = "";
    lastRowsJson = rowsJson;
    lastColumnsJson = columnsJson;
    createGrid(root, columnDefs);
  }

  window.addEventListener("message", function (event) {
    var data = event.data;
    if (!data || data.type !== "streamlit:render") return;
    renderGrid(data.args || {});
  });

  sendToStreamlit("streamlit:componentReady", { apiVersion: 1 });
})();
