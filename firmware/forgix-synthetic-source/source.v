// Prospective synthetic source v1. No external input or configuration writer.
// Classic, non-pipelined Wishbone-style local byte-addressed register port.
// SYSTEM_HZ is pinned to32000000 by the production RTL wrapper; a smaller
// value is used only for cycle-scaled simulations. No SPI timing is changed.
module forgix_synthetic_source #(
    parameter integer SYSTEM_HZ = 32000000
)(
    input wire clk, input wire reset,
    input wire wb_cyc, input wire wb_stb, input wire wb_we,
    input wire [11:0] wb_addr, input wire [31:0] wb_data_in,
    input wire [3:0] wb_sel,
    output reg wb_ack, output reg wb_err, output reg [31:0] wb_data_out
);
    localparam integer DEPTH = 64;
    localparam [31:0] RATE0 = SYSTEM_HZ / 16;
    localparam [31:0] RATE1 = SYSTEM_HZ / 64;
    localparam [31:0] RATE2 = SYSTEM_HZ / 128;
    localparam [63:0] START_WINDOW = SYSTEM_HZ * 64'd30;
    localparam [63:0] DRAIN_CYCLES = SYSTEM_HZ * 64'd5;
    localparam [63:0] PAUSE_CYCLES = SYSTEM_HZ / 10;
    reg seen;
    reg [63:0] tick, start_tick, stop_tick, pause_begin, pause_end;
    reg [63:0] drain_until;
    reg [31:0] period_cfg, target_cfg, period_active, target_active;
    reg [127:0] nonce_cfg, nonce_active;
    reg attempted, accepted, running, done, pause_attempted;
    reg [31:0] next_due;
    // Reload at START and each offered record. Zero is the exact due edge.
    // This avoids a 64-bit timestamp subtraction on the completion-enable path.
    reg [31:0] due_left;
    reg [31:0] generated_count, enqueued_count, dropped_count, popped_count;
    reg [31:0] refused_pop, refused_command;
    reg [6:0] level, high_water;
    reg [5:0] write_pointer, read_pointer;
    reg [127:0] fifo [0:DEPTH-1];
    reg [127:0] head;
    reg [1:0] head_wait;
    // Separate synchronous read port. The two-cycle valid delay after empty
    // enqueue/POP makes read-during-write results irrelevant to public HEAD.
    always @(posedge clk) head <= fifo[read_pointer];

    wire fire = wb_cyc && wb_stb && !seen;
    wire aligned = wb_addr[1:0] == 0;
    wire write_fire = fire && wb_we && aligned && wb_sel == 4'hf;
    wire head_valid = level != 0 && head_wait == 0;
    wire pause_active = pause_attempted && tick < pause_end;
    wire drain_expired = done && tick >= drain_until;
    wire pop_request = write_fire && wb_addr == 12'h040;
    wire pop_ok = pop_request && head_valid && !pause_active && !drain_expired && wb_data_in == head[31:0];
    wire due = running && due_left == 0;
    wire push = due && (level < DEPTH || pop_ok);
    wire config_ok = nonce_cfg != 0 &&
        ((period_cfg == RATE0 && target_cfg == 960) ||
         (period_cfg == RATE1 && target_cfg == 3840) ||
         (period_cfg == RATE2 && target_cfg == 7680));
    wire [31:0] pattern = generated_count ^
        {generated_count[24:0], generated_count[31:25]} ^
        nonce_active[31:0] ^ nonce_active[63:32] ^
        nonce_active[95:64] ^ nonce_active[127:96] ^ 32'h46534731;
    wire [95:0] record_body = {pattern, tick[31:0], generated_count};
    function [31:0] record_crc;
        input [95:0] bytes_le;
        reg [31:0] crc;
        integer byte_number, bit_number;
        begin
            crc = 32'hffffffff;
            for (byte_number = 0; byte_number < 12; byte_number = byte_number + 1) begin
                crc = crc ^ ((bytes_le >> (8 * byte_number)) & 32'hff);
                for (bit_number = 0; bit_number < 8; bit_number = bit_number + 1)
                    crc = (crc >> 1) ^ (crc[0] ? 32'hedb88320 : 32'h0);
            end
            record_crc = ~crc;
        end
    endfunction

    reg [31:0] snapshot_id;
    reg [63:0] snapshot_tick, snapshot_start, snapshot_stop;
    reg [31:0] snap_generated, snap_enqueued, snap_dropped, snap_popped;
    reg [31:0] snap_refused_pop, snap_refused_command, snap_state;
    reg [6:0] snap_level, snap_high_water;
    wire [31:0] live_state = {25'b0, accepted, drain_expired, pause_active,
                             head_valid, done, running, attempted};
    // Bit7 remains reserved zero; only bits0..6 of live_state are defined.

    always @* begin
        wb_data_out = 0;
        if (aligned) case (wb_addr)
            12'h000: wb_data_out = 32'h46534731; // FSG1, distinct from register bridge.
            12'h004: wb_data_out = SYSTEM_HZ;
            12'h008: wb_data_out = 32'h00074010; // rates0..2, depth64, record16bytes.
            12'h010: wb_data_out = period_cfg;
            12'h014: wb_data_out = target_cfg;
            12'h018: wb_data_out = nonce_cfg[31:0];
            12'h01c: wb_data_out = nonce_cfg[63:32];
            12'h020: wb_data_out = nonce_cfg[95:64];
            12'h024: wb_data_out = nonce_cfg[127:96];
            12'h028: wb_data_out = live_state;
            12'h02c: wb_data_out = level;
            12'h030: wb_data_out = high_water;
            12'h034: wb_data_out = head_valid ? head[31:0] : 0;
            12'h038: wb_data_out = head_valid ? head[63:32] : 0;
            12'h03c: wb_data_out = head_valid ? head[95:64] : 0;
            12'h044: wb_data_out = head_valid ? head[127:96] : 0;
            12'h048: wb_data_out = popped_count; // POP readback, live.
            12'h04c: wb_data_out = snapshot_id;
            12'h050: wb_data_out = snapshot_tick[31:0];
            12'h054: wb_data_out = snapshot_tick[63:32];
            12'h058: wb_data_out = snap_state;
            12'h05c: wb_data_out = snap_generated;
            12'h060: wb_data_out = snap_enqueued;
            12'h064: wb_data_out = snap_dropped;
            12'h068: wb_data_out = snap_popped;
            12'h06c: wb_data_out = snap_refused_pop;
            12'h070: wb_data_out = snap_refused_command;
            12'h074: wb_data_out = snap_level;
            12'h078: wb_data_out = snap_high_water;
            12'h07c: wb_data_out = snapshot_start[31:0];
            12'h080: wb_data_out = snapshot_start[63:32];
            12'h084: wb_data_out = snapshot_stop[31:0];
            12'h088: wb_data_out = snapshot_stop[63:32];
            12'h08c: wb_data_out = pause_begin[31:0];
            12'h090: wb_data_out = pause_begin[63:32];
            12'h094: wb_data_out = pause_end[31:0];
            12'h098: wb_data_out = pause_end[63:32];
            default: wb_data_out = 0;
        endcase
    end

    always @(posedge clk) begin
        if (reset) begin
            seen <= 0; wb_ack <= 0; wb_err <= 0; tick <= 0;
            start_tick <= 0; stop_tick <= 0; pause_begin <= 0; pause_end <= 0;
            drain_until <= 0;
            period_cfg <= 0; target_cfg <= 0; nonce_cfg <= 0;
            period_active <= 0; target_active <= 0; nonce_active <= 0;
            attempted <= 0; accepted <= 0; running <= 0; done <= 0; pause_attempted <= 0;
            due_left <= 0;
            next_due <= 0; generated_count <= 0; enqueued_count <= 0;
            dropped_count <= 0; popped_count <= 0; refused_pop <= 0; refused_command <= 0;
            level <= 0; high_water <= 0; write_pointer <= 0; read_pointer <= 0; head_wait <= 0;
            snapshot_id <= 0; snapshot_tick <= 0; snapshot_start <= 0; snapshot_stop <= 0;
            snap_generated <= 0; snap_enqueued <= 0; snap_dropped <= 0; snap_popped <= 0;
            snap_refused_pop <= 0; snap_refused_command <= 0; snap_state <= 0;
            snap_level <= 0; snap_high_water <= 0;
        end else begin
            tick <= tick + 1;
            wb_ack <= 0; wb_err <= 0;
            if (!wb_cyc || !wb_stb) seen <= 0;
            if (head_wait != 0) head_wait <= head_wait - 1;
            if (running) begin
                if (due) due_left <= period_active - 1;
                else due_left <= due_left - 1;
            end
            if (due) begin
                generated_count <= generated_count + 1;
                next_due <= next_due + period_active;
                if (generated_count + 1 == target_active) begin
                    running <= 0; done <= 1; stop_tick <= tick;
                    drain_until <= tick + DRAIN_CYCLES;
                end
                if (push) begin
                    fifo[write_pointer] <= {record_crc(record_body), record_body};
                    write_pointer <= write_pointer + 1;
                    enqueued_count <= enqueued_count + 1;
                    if (level == 0) head_wait <= 2;
                end else dropped_count <= dropped_count + 1;
            end
            if (pop_ok) begin
                popped_count <= popped_count + 1;
                read_pointer <= read_pointer + 1;
                head_wait <= 2;
            end
            case ({push, pop_ok})
                2'b10: begin
                    level <= level + 1;
                    if (level + 1 > high_water) high_water <= level + 1;
                end
                2'b01: level <= level - 1;
                default: ;
            endcase
            if (fire) begin
                seen <= 1;
                wb_ack <= 1;
                if (!aligned || (wb_we && wb_sel != 4'hf)) begin
                    wb_err <= 1; refused_command <= refused_command + 1;
                end else if (wb_we) begin
                    case (wb_addr)
                        12'h010, 12'h014, 12'h018, 12'h01c, 12'h020, 12'h024:
                            if (attempted) begin wb_err <= 1; refused_command <= refused_command + 1; end
                            else case (wb_addr)
                                12'h010: period_cfg <= wb_data_in;
                                12'h014: target_cfg <= wb_data_in;
                                12'h018: nonce_cfg[31:0] <= wb_data_in;
                                12'h01c: nonce_cfg[63:32] <= wb_data_in;
                                12'h020: nonce_cfg[95:64] <= wb_data_in;
                                12'h024: nonce_cfg[127:96] <= wb_data_in;
                            endcase
                        12'h00c: case (wb_data_in)
                            1: begin
                                if (attempted) begin wb_err <= 1; refused_command <= refused_command + 1; end
                                else begin
                                    attempted <= 1;
                                    if (tick >= START_WINDOW || !config_ok) begin wb_err <= 1; refused_command <= refused_command + 1; end
                                    else begin
                                        accepted <= 1; running <= 1; start_tick <= tick;
                                        period_active <= period_cfg; target_active <= target_cfg;
                                        nonce_active <= nonce_cfg; next_due <= period_cfg;
                                        due_left <= period_cfg - 1;
                                    end
                                end
                            end
                            2: if (running) begin
                                   running <= 0; done <= 1; stop_tick <= tick;
                                   drain_until <= tick + DRAIN_CYCLES;
                               end
                               else begin wb_err <= 1; refused_command <= refused_command + 1; end
                            4: begin
                                snapshot_id <= snapshot_id + 1; snapshot_tick <= tick;
                                snapshot_start <= start_tick; snapshot_stop <= stop_tick;
                                snap_generated <= generated_count; snap_enqueued <= enqueued_count;
                                snap_dropped <= dropped_count; snap_popped <= popped_count;
                                snap_refused_pop <= refused_pop; snap_refused_command <= refused_command;
                                snap_state <= live_state; snap_level <= level; snap_high_water <= high_water;
                            end
                            8: if (running && !pause_attempted) begin
                                   pause_attempted <= 1; pause_begin <= tick; pause_end <= tick + PAUSE_CYCLES;
                               end else begin wb_err <= 1; refused_command <= refused_command + 1; end
                            default: begin wb_err <= 1; refused_command <= refused_command + 1; end
                        endcase
                        12'h040: if (!pop_ok) begin wb_err <= 1; refused_pop <= refused_pop + 1; end
                        default: begin wb_err <= 1; refused_command <= refused_command + 1; end
                    endcase
                end else begin
                    // Reads from write-only/control, reserved and unaligned
                    // locations are errors. Caller must inspect readback because
                    // the existing SPIBone protocol cannot distinguish ACK/ERR.
                    case (wb_addr)
                        12'h000,12'h004,12'h008,12'h010,12'h014,12'h018,12'h01c,12'h020,12'h024,
                        12'h028,12'h02c,12'h030,12'h034,12'h038,12'h03c,12'h044,12'h048,
                        12'h04c,12'h050,12'h054,12'h058,12'h05c,12'h060,12'h064,12'h068,
                        12'h06c,12'h070,12'h074,12'h078,12'h07c,12'h080,12'h084,12'h088,
                        12'h08c,12'h090,12'h094,12'h098: ;
                        default: begin wb_err <= 1; refused_command <= refused_command + 1; end
                    endcase
                end
            end
        end
    end
endmodule
