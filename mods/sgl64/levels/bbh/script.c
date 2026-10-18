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
#include "levels/bbh/header.h"

/* Fast64 begin persistent block [scripts] */
/* Fast64 end persistent block [scripts] */

const LevelScript level_bbh_entry[] = {
	INIT_LEVEL(),
	LOAD_MIO0(0x07, _bbh_segment_7SegmentRomStart, _bbh_segment_7SegmentRomEnd),
	ALLOC_LEVEL_POOL(),
	MARIO(MODEL_MARIO, 0x00000001, bhvMario),
	JUMP_LINK(script_func_global_1),
	/* Fast64 begin persistent block [level commands] */
	/* Fast64 end persistent block [level commands] */

	AREA(1, bbh_area_1),
		WARP_NODE(0x0A, LEVEL_BBH, 0x01, 0x0A, WARP_NO_CHECKPOINT),
		WARP_NODE(0xF0, LEVEL_CASTLE_GROUNDS, 0x01, 0x25, WARP_NO_CHECKPOINT),
		WARP_NODE(0xF1, LEVEL_CASTLE_GROUNDS, 0x01, 0x35, WARP_NO_CHECKPOINT),
		OBJECT(MODEL_1UP, -778, 1560, -2630, 0, -180, 0, 0x00000000, bhv1Up),
		OBJECT(MODEL_1UP, 610, 2460, 2410, 0, -180, 0, 0x00000000, bhv1Up),
		OBJECT(MODEL_1UP, 2005, 2460, -2785, 0, -180, 0, 0x00000000, bhv1Up),
		MARIO_POS(0x01, -180, 0, 100, 2320),
		OBJECT(MODEL_NONE, 0, 100, 2320, 0, -180, 0, 0x000A0000, bhvSpinAirborneWarp),
		OBJECT(MODEL_HEART, -810, 100, 1890, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_HEART, -15, 700, -2420, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_HEART, -1690, 1900, -1440, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_HEART, -2370, 3100, 1480, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		TERRAIN(bbh_area_1_collision),
		MACRO_OBJECTS(bbh_area_1_macro_objs),
		SET_BACKGROUND_MUSIC(0x00, SEQ_LEVEL_SPOOKY),
		TERRAIN_TYPE(TERRAIN_SPOOKY),
		/* Fast64 begin persistent block [area commands] */
		/* Fast64 end persistent block [area commands] */
	END_AREA(),
	FREE_LEVEL_POOL(),
	MARIO_POS(0x01, -180, 0, 100, 2320),
	CALL(0, lvl_init_or_update),
	CALL_LOOP(1, lvl_init_or_update),
	CLEAR_LEVEL(),
	SLEEP_BEFORE_EXIT(1),
	EXIT(),
};