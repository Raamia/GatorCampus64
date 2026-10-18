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
#include "levels/bob/header.h"

/* Fast64 begin persistent block [scripts] */
/* Fast64 end persistent block [scripts] */

const LevelScript level_bob_entry[] = {
	INIT_LEVEL(),
	LOAD_MIO0(0x07, _bob_segment_7SegmentRomStart, _bob_segment_7SegmentRomEnd),
	LOAD_MIO0(0x0A, _water_skybox_mio0SegmentRomStart, _water_skybox_mio0SegmentRomEnd),
	ALLOC_LEVEL_POOL(),
	MARIO(MODEL_MARIO, 0x00000001, bhvMario),
	JUMP_LINK(script_func_global_1),
	/* Fast64 begin persistent block [level commands] */
	/* Fast64 end persistent block [level commands] */

	AREA(1, bob_area_1),
		WARP_NODE(0x0A, LEVEL_BOB, 0x01, 0x0A, WARP_NO_CHECKPOINT),
		WARP_NODE(0xF0, LEVEL_CASTLE_GROUNDS, 0x01, 0x21, WARP_NO_CHECKPOINT),
		WARP_NODE(0xF1, LEVEL_CASTLE_GROUNDS, 0x01, 0x31, WARP_NO_CHECKPOINT),
		OBJECT(MODEL_1UP, -17860, 3170, 9215, 0, -180, 0, 0x00000000, bhv1Up),
		OBJECT(MODEL_1UP, 19677, 1820, 14917, 0, -180, 0, 0x00000000, bhv1Up),
		OBJECT(MODEL_1UP, -2284, 7160, 4856, 0, -180, 0, 0x00000000, bhv1Up),
		OBJECT(MODEL_NONE, 5100, 0, -10200, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 8200, 0, -10200, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 5100, 0, -12600, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 8200, 0, -12600, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 4500, 0, -8400, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 8800, 0, -8400, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 2000, 0, 17350, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 5000, 0, 17400, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 14000, 0, 16900, 0, 0, 0, 0x002B0000, bhvPoleGrabbing),
		MARIO_POS(0x01, 0, 6651, 100, -11298),
		OBJECT(MODEL_NONE, 6651, 100, -11298, 0, 0, 0, 0x000A0000, bhvSpinAirborneWarp),
		OBJECT_WITH_ACTS(MODEL_STAR, -3828, 6720, 3648, 0, 0, 0, 0x00000000, bhvStar, ACT_1),
		OBJECT(MODEL_HEART, -2173, 4500, 3656, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_HEART, 6508, 2100, 15832, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_HEART, -1904, 5500, 3778, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_HEART, -2457, 2100, 8355, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_NONE, -1825, 4400, 3108, 0, -180, 0, 0x00E10000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 15781, 2100, 7800, 0, -180, 0, 0x00780000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 15803, 2100, 3491, 0, -180, 0, 0x00780000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 15826, 2100, -799, 0, -180, 0, 0x00780000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 6602, -1000, -1964, 0, -180, 0, 0x001E0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 6542, -1000, 9368, 0, -180, 0, 0x001E0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 5280, 2000, 15745, 0, -180, 0, 0x00F20000, bhvPoleGrabbing),
		TERRAIN(bob_area_1_collision),
		MACRO_OBJECTS(bob_area_1_macro_objs),
		SET_BACKGROUND_MUSIC(0x00, SEQ_LEVEL_SNOW),
		TERRAIN_TYPE(TERRAIN_GRASS),
		/* Fast64 begin persistent block [area commands] */
		/* Fast64 end persistent block [area commands] */
		OBJECT(MODEL_GOOMBA, 11677, 0, 3729, 0, 0, 0, 0x00000000, bhvGoomba),
		OBJECT(MODEL_GOOMBA, 4886, 0, -4262, 0, 90, 0, 0x00000000, bhvGoomba),
		OBJECT(MODEL_GOOMBA, 1467, 0, 3675, 0, 180, 0, 0x00000000, bhvGoomba),
		OBJECT(MODEL_GOOMBA, 7436, 0, -8506, 0, -156, 0, 0x00000000, bhvGoomba),
		OBJECT(MODEL_GOOMBA, 5836, 0, -8514, 0, 156, 0, 0x00000000, bhvGoomba),
		OBJECT(MODEL_GOOMBA, 15540, 2000, 5999, 0, 180, 0, 0x00000000, bhvGoomba),
		OBJECT(MODEL_GOOMBA, 11095, 2000, 14578, 0, 112, 0, 0x00000000, bhvGoomba),
	END_AREA(),
	FREE_LEVEL_POOL(),
	MARIO_POS(0x01, 0, 6651, 100, -11298),
	CALL(0, lvl_init_or_update),
	CALL_LOOP(1, lvl_init_or_update),
	CLEAR_LEVEL(),
	SLEEP_BEFORE_EXIT(1),
	EXIT(),
};