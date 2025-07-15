def save_ticket(
    ticket_number, vehicle_number, date_str, time_str,
    empty_weight, loaded_weight, empty_weight_date, empty_weight_time,
    load_weight_date, load_weight_time, net_weight, pending, closed, exported,
    shift, materialname, suppliername, state, blank, amount, status, eamount, lamount, tamount, netweight1, lweight, eweight
):
    sql = """
    INSERT INTO tickets (
        "TicketNumber", "VehicleNumber", "Date", "Time",
        "EmptyWeight", "LoadedWeight", "EmptyWeightDate", "EmptyWeightTime",
        "LoadWeightDate", "LoadWeightTime", "NetWeight", "Pending", "Closed", "Exported",
        "Shift", "Materialname", "SupplierName", "State", "Blank", "AMOUNT", "STATUS",
        "EAMOUNT", "LAMOUNT", "TAMOUNT", "NetWeight1", "LWEIGHT", "EWEIGHT"
    ) VALUES (
        %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s
    )
    ON CONFLICT ("TicketNumber") DO UPDATE SET
        "VehicleNumber" = EXCLUDED."VehicleNumber",
        "Date" = EXCLUDED."Date",
        "Time" = EXCLUDED."Time",
        "EmptyWeight" = EXCLUDED."EmptyWeight",
        "LoadedWeight" = EXCLUDED."LoadedWeight",
        "EmptyWeightDate" = EXCLUDED."EmptyWeightDate",
        "EmptyWeightTime" = EXCLUDED."EmptyWeightTime",
        "LoadWeightDate" = EXCLUDED."LoadWeightDate",
        "LoadWeightTime" = EXCLUDED."LoadWeightTime",
        "NetWeight" = EXCLUDED."NetWeight",
        "Pending" = EXCLUDED."Pending",
        "Closed" = EXCLUDED."Closed",
        "Exported" = EXCLUDED."Exported",
        "Shift" = EXCLUDED."Shift",
        "Materialname" = EXCLUDED."Materialname",
        "SupplierName" = EXCLUDED."SupplierName",
        "State" = EXCLUDED."State",
        "Blank" = EXCLUDED."Blank",
        "AMOUNT" = EXCLUDED."AMOUNT",
        "STATUS" = EXCLUDED."STATUS",
        "EAMOUNT" = EXCLUDED."EAMOUNT",
        "LAMOUNT" = EXCLUDED."LAMOUNT",
        "TAMOUNT" = EXCLUDED."TAMOUNT",
        "NetWeight1" = EXCLUDED."NetWeight1",
        "LWEIGHT" = EXCLUDED."LWEIGHT",
        "EWEIGHT" = EXCLUDED."EWEIGHT"
    ;
    """
    params = (
        ticket_number, vehicle_number, date_str, time_str,
        empty_weight, loaded_weight, empty_weight_date, empty_weight_time,
        load_weight_date, load_weight_time, net_weight, pending, closed, exported,
        shift, materialname, suppliername, state, blank, amount, status, eamount, lamount, tamount, netweight1, lweight, eweight
    )
    execute_query(sql, params)