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
#include "levels/ccm/header.h"

/* Fast64 begin persistent block [scripts] */
/* Fast64 end persistent block [scripts] */

const LevelScript level_ccm_entry[] = {
	INIT_LEVEL(),
	LOAD_MIO0(0x07, _ccm_segment_7SegmentRomStart, _ccm_segment_7SegmentRomEnd),
	LOAD_MIO0(0x0A, _water_skybox_mio0SegmentRomStart, _water_skybox_mio0SegmentRomEnd),
	ALLOC_LEVEL_POOL(),
	MARIO(MODEL_MARIO, 0x00000001, bhvMario),
	JUMP_LINK(script_func_global_1),
	/* Fast64 begin persistent block [level commands] */
	/* Fast64 end persistent block [level commands] */

	AREA(1, ccm_area_1),
		WARP_NODE(0x0A, LEVEL_CCM, 0x01, 0x0A, WARP_NO_CHECKPOINT),
		WARP_NODE(0xF0, LEVEL_CASTLE_GROUNDS, 0x01, 0x24, WARP_NO_CHECKPOINT),
		WARP_NODE(0xF1, LEVEL_CASTLE_GROUNDS, 0x01, 0x34, WARP_NO_CHECKPOINT),
		OBJECT(MODEL_1UP, 1350, 3030, -2590, 0, -180, 0, 0x00000000, bhv1Up),
		OBJECT(MODEL_1UP, -2554, 3080, 1448, 0, -180, 0, 0x00000000, bhv1Up),
		OBJECT(MODEL_1UP, -80, 1560, 150, 0, -180, 0, 0x00000000, bhv1Up),
		OBJECT(MODEL_1UP, -2258, -280, -4310, 0, -180, 0, 0x00000000, bhv1Up),
		MARIO_POS(0x01, 0, -790, 100, -1510),
		OBJECT(MODEL_NONE, -790, 100, -1510, 0, 0, 0, 0x000A0000, bhvSpinAirborneWarp),
		OBJECT(MODEL_HEART, -40, -500, -690, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_HEART, -740, 700, 110, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_HEART, 260, 1900, -790, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_HEART, -1040, 2500, -1990, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		TERRAIN(ccm_area_1_collision),
		MACRO_OBJECTS(ccm_area_1_macro_objs),
		SET_BACKGROUND_MUSIC(0x00, SEQ_LEVEL_INSIDE_CASTLE),
		TERRAIN_TYPE(TERRAIN_STONE),
		/* Fast64 begin persistent block [area commands] */
		/* Fast64 end persistent block [area commands] */
	END_AREA(),
	FREE_LEVEL_POOL(),
	MARIO_POS(0x01, 0, -790, 100, -1510),
	CALL(0, lvl_init_or_update),
	CALL_LOOP(1, lvl_init_or_update),
	CLEAR_LEVEL(),
	SLEEP_BEFORE_EXIT(1),
	EXIT(),
};