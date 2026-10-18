#include <ultra64.h>
#include "sm64.h"
#include "behavior_data.h"
#include "model_ids.h"
#include "seq_ids.h"
#include "dialog_ids.h"
#include "segment_symbols.h"
#include "level_commands.h"

#include "game/level_update.h"

#include "levels/scripts.h"

#include "make_const_nonconst.h"
#include "levels/wf/header.h"

/* Fast64 begin persistent block [scripts] */
/* Fast64 end persistent block [scripts] */

const LevelScript level_wf_entry[] = {
	INIT_LEVEL(),
	LOAD_MIO0(0x07, _wf_segment_7SegmentRomStart, _wf_segment_7SegmentRomEnd),
	LOAD_MIO0(0x0A, _water_skybox_mio0SegmentRomStart, _water_skybox_mio0SegmentRomEnd),
	ALLOC_LEVEL_POOL(),
	MARIO(MODEL_MARIO, 0x00000001, bhvMario),
	JUMP_LINK(script_func_global_1),
	/* Fast64 begin persistent block [level commands] */
	/* Fast64 end persistent block [level commands] */

	AREA(1, wf_area_1),
		WARP_NODE(0x0A, LEVEL_WF, 0x01, 0x0A, WARP_NO_CHECKPOINT),
		WARP_NODE(0xF0, LEVEL_CASTLE_GROUNDS, 0x01, 0x22, WARP_NO_CHECKPOINT),
		WARP_NODE(0xF1, LEVEL_CASTLE_GROUNDS, 0x01, 0x32, WARP_NO_CHECKPOINT),
		INSTANT_WARP(0x00, 0x02, 0, 0, 0),
		INSTANT_WARP(0x01, 0x02, 0, 600, 0),
		INSTANT_WARP(0x02, 0x02, 0, -200, 0),
		INSTANT_WARP(0x03, 0x02, 0, 400, 0),
		OBJECT(MODEL_1UP, -375, 3827, 23850, 0, -180, 0, 0x00000000, bhv1Up),
		OBJECT(MODEL_1UP, -5225, 1620, -2802, 0, -180, 0, 0x00000000, bhv1Up),
		OBJECT(MODEL_1UP, 1150, 2620, -24800, 0, -180, 0, 0x00000000, bhv1Up),
		OBJECT(MODEL_NONE, 1800, 0, -7100, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 3200, 0, -5700, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 150, 0, -6000, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 6000, 0, -6000, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 9200, 0, -5750, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 12500, 0, -6700, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 16500, 0, -7900, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 8200, 0, -9000, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 14000, 0, -12500, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 19400, 0, -10100, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 0, 0, 20600, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 3600, 0, 20600, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		MARIO_POS(0x01, -34, 7200, 100, -9300),
		OBJECT(MODEL_NONE, 7200, 100, -9300, 0, -34, 0, 0x000A0000, bhvSpinAirborneWarp),
		OBJECT(MODEL_BLACK_BOBOMB, -2200, 1320, -3200, 0, 90, 0, 0x00000000, bhvBobomb),
		OBJECT(MODEL_BLACK_BOBOMB, 3400, 2640, -3700, 0, -90, 0, 0x00000000, bhvBobomb),
		OBJECT(MODEL_HEART, 5126, 1767, 22015, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_HEART, 7800, 300, 450, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_HEART, 1000, 1860, -3200, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_HEART, 160, 1460, -23690, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_NONE, 880, 0, -5580, 0, -180, 0, 0x00320000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 1580, 0, -23545, 0, -180, 0, 0x00940000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 1385, 0, -22955, 0, -180, 0, 0x006C0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -490, 0, -25534, 0, -180, 0, 0x00940000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -7640, 0, -25534, 0, -180, 0, 0x00940000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -5190, 0, -23545, 0, -180, 0, 0x00940000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -9040, 0, -23480, 0, -180, 0, 0x00940000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -9045, 0, -24975, 0, -180, 0, 0x00680000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 1300, 1760, -2640, 0, -180, 0, 0x005A0000, bhvPoleGrabbing),
		OBJECT(MODEL_KOOPA_SHELL, -12800, 0, -21100, 0, -180, 0, 0x00000000, bhvKoopaShell),
		OBJECT(MODEL_KOOPA_SHELL, 7697, 0, -8964, 0, -180, 0, 0x00000000, bhvKoopaShell),
		OBJECT(MODEL_KOOPA_SHELL, -6600, 0, 1900, 0, -180, 0, 0x00000000, bhvKoopaShell),
		TERRAIN(wf_area_1_collision),
		MACRO_OBJECTS(wf_area_1_macro_objs),
		SET_BACKGROUND_MUSIC(0x00, SEQ_LEVEL_HOT),
		TERRAIN_TYPE(TERRAIN_GRASS),
		/* Fast64 begin persistent block [area commands] */
		/* Fast64 end persistent block [area commands] */
	END_AREA(),
	AREA(2, wf_area_2),
		WARP_NODE(0x0A, LEVEL_WF, 0x02, 0x0A, WARP_NO_CHECKPOINT),
		WARP_NODE(0xF0, LEVEL_CASTLE_GROUNDS, 0x01, 0x22, WARP_NO_CHECKPOINT),
		WARP_NODE(0xF1, LEVEL_CASTLE_GROUNDS, 0x01, 0x32, WARP_NO_CHECKPOINT),
		WARP_NODE(0x40, LEVEL_WF, 0x02, 0x41, WARP_NO_CHECKPOINT),
		WARP_NODE(0x41, LEVEL_WF, 0x02, 0x40, WARP_NO_CHECKPOINT),
		WARP_NODE(0x42, LEVEL_WF, 0x02, 0x43, WARP_NO_CHECKPOINT),
		WARP_NODE(0x43, LEVEL_WF, 0x02, 0x42, WARP_NO_CHECKPOINT),
		WARP_NODE(0x44, LEVEL_WF, 0x02, 0x45, WARP_NO_CHECKPOINT),
		WARP_NODE(0x45, LEVEL_WF, 0x02, 0x44, WARP_NO_CHECKPOINT),
		WARP_NODE(0x46, LEVEL_WF, 0x02, 0x47, WARP_NO_CHECKPOINT),
		WARP_NODE(0x47, LEVEL_WF, 0x02, 0x46, WARP_NO_CHECKPOINT),
		WARP_NODE(0x48, LEVEL_WF, 0x02, 0x49, WARP_NO_CHECKPOINT),
		WARP_NODE(0x49, LEVEL_WF, 0x02, 0x48, WARP_NO_CHECKPOINT),
		WARP_NODE(0x4A, LEVEL_WF, 0x02, 0x4B, WARP_NO_CHECKPOINT),
		WARP_NODE(0x4B, LEVEL_WF, 0x02, 0x4A, WARP_NO_CHECKPOINT),
		WARP_NODE(0x4C, LEVEL_WF, 0x02, 0x4D, WARP_NO_CHECKPOINT),
		WARP_NODE(0x4D, LEVEL_WF, 0x02, 0x4C, WARP_NO_CHECKPOINT),
		INSTANT_WARP(0x00, 0x01, 0, 0, 0),
		INSTANT_WARP(0x01, 0x01, 0, -600, 0),
		INSTANT_WARP(0x02, 0x01, 0, 200, 0),
		INSTANT_WARP(0x03, 0x01, 0, -400, 0),
		OBJECT(MODEL_NONE, 2872, 0, -2377, 0, -90, 0, 0x07410000, bhvFadingWarp),
		OBJECT(MODEL_NONE, 2124, 0, -2378, 0, 90, 0, 0x07420000, bhvFadingWarp),
		OBJECT(MODEL_NONE, 2856, 600, -2307, 0, -90, 0, 0x07430000, bhvFadingWarp),
		OBJECT(MODEL_NONE, 2163, 600, -2317, 0, 90, 0, 0x07440000, bhvFadingWarp),
		OBJECT(MODEL_NONE, 2880, 1200, -2370, 0, -90, 0, 0x07450000, bhvFadingWarp),
		OBJECT(MODEL_NONE, 2135, 1200, -2380, 0, 90, 0, 0x07460000, bhvFadingWarp),
		OBJECT(MODEL_NONE, 2810, 1800, -2365, 0, -90, 0, 0x07470000, bhvFadingWarp),
		OBJECT(MODEL_NONE, 2114, 1800, -2373, 0, 90, 0, 0x07480000, bhvFadingWarp),
		OBJECT(MODEL_NONE, 2891, 2400, -2407, 0, -90, 0, 0x07490000, bhvFadingWarp),
		OBJECT(MODEL_NONE, 2110, 2400, -2415, 0, 90, 0, 0x074A0000, bhvFadingWarp),
		OBJECT(MODEL_NONE, 2880, 2900, -2300, 0, -90, 0, 0x074B0000, bhvFadingWarp),
		OBJECT(MODEL_NONE, 2127, 2900, -2307, 0, 90, 0, 0x074C0000, bhvFadingWarp),
		OBJECT(MODEL_NONE, 2875, 3400, -2305, 0, -90, 0, 0x074D0000, bhvFadingWarp),
		OBJECT(MODEL_NONE, 2124, -600, -2333, 0, 90, 0, 0x07400000, bhvFadingWarp),
		OBJECT(MODEL_NONE, 7100, 100, -1450, 0, -180, 0, 0x000A0000, bhvSpinAirborneWarp),
		OBJECT(MODEL_HEART, 3000, 3000, -1900, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_1UP, 5260, 60, 660, 0, -180, 0, 0x00000000, bhv1Up),
		OBJECT(MODEL_1UP, 7270, 150, -2190, 0, -180, 0, 0x00000000, bhv1Up),
		OBJECT(MODEL_1UP, 5867, 320, -2740, 0, -180, 0, 0x00000000, bhv1Up),
		TERRAIN(wf_area_2_collision),
		MACRO_OBJECTS(wf_area_2_macro_objs),
		SET_BACKGROUND_MUSIC(0x00, SEQ_LEVEL_HOT),
		TERRAIN_TYPE(TERRAIN_STONE),
		/* Fast64 begin persistent block [area commands] */
		/* Fast64 end persistent block [area commands] */
	END_AREA(),
	FREE_LEVEL_POOL(),
	MARIO_POS(0x01, -34, 7200, 100, -9300),
	CALL(0, lvl_init_or_update),
	CALL_LOOP(1, lvl_init_or_update),
	CLEAR_LEVEL(),
	SLEEP_BEFORE_EXIT(1),
	EXIT(),
};