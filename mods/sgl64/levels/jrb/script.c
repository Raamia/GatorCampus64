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
#include "levels/jrb/header.h"

/* Fast64 begin persistent block [scripts] */
/* Fast64 end persistent block [scripts] */

const LevelScript level_jrb_entry[] = {
	INIT_LEVEL(),
	LOAD_MIO0(0x07, _jrb_segment_7SegmentRomStart, _jrb_segment_7SegmentRomEnd),
	LOAD_MIO0(0x0A, _water_skybox_mio0SegmentRomStart, _water_skybox_mio0SegmentRomEnd),
	ALLOC_LEVEL_POOL(),
	MARIO(MODEL_MARIO, 0x00000001, bhvMario),
	JUMP_LINK(script_func_global_1),
	/* Fast64 begin persistent block [level commands] */
	/* Fast64 end persistent block [level commands] */

	AREA(1, jrb_area_1),
		WARP_NODE(0x0A, LEVEL_JRB, 0x01, 0x0A, WARP_NO_CHECKPOINT),
		WARP_NODE(0xF0, LEVEL_CASTLE_GROUNDS, 0x01, 0x23, WARP_NO_CHECKPOINT),
		WARP_NODE(0xF1, LEVEL_CASTLE_GROUNDS, 0x01, 0x33, WARP_NO_CHECKPOINT),
		OBJECT(MODEL_1UP, -14616, 608, -15745, 0, -180, 0, 0x00000000, bhv1Up),
		OBJECT(MODEL_1UP, 6000, -436, -5500, 0, -180, 0, 0x00000000, bhv1Up),
		OBJECT(MODEL_1UP, 2590, 460, -470, 0, -180, 0, 0x00000000, bhv1Up),
		MARIO_POS(0x01, 30, -13300, 100, -11900),
		OBJECT(MODEL_NONE, -13300, 100, -11900, 0, 30, 0, 0x000A0000, bhvSpinAirborneWarp),
		OBJECT(MODEL_HEART, -18668, 100, 7190, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_HEART, 24219, 100, -2833, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_HEART, -9006, 100, -4710, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_HEART, 9000, 88, -16650, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_HEART, 2281, 120, -520, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_NONE, -11885, 0, -14599, 0, -180, 0, 0x00530000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -14546, 0, -15910, 0, -180, 0, 0x00530000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -18900, -72, 4600, 0, -180, 0, 0x00430000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 21139, -63, -522, 0, -180, 0, 0x00420000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 6411, -62, 19214, 0, -180, 0, 0x00580000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -7042, -62, 16125, 0, -180, 0, 0x00480000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -10470, -52, 10465, 0, -180, 0, 0x004C0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 3006, -73, 20089, 0, -180, 0, 0x004B0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 765, -73, 20282, 0, -180, 0, 0x00550000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -10152, -57, 14993, 0, -180, 0, 0x00590000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -16500, -46, 6450, 0, -180, 0, 0x00450000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -9200, 0, -4250, 0, -180, 0, 0x00520000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 2684, -65, 13140, 0, -180, 0, 0x00460000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -4898, -57, -8402, 0, -180, 0, 0x00530000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -10155, -43, 17480, 0, -180, 0, 0x004F0000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 19309, -58, 3838, 0, -180, 0, 0x00460000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -10462, -89, 7048, 0, -180, 0, 0x00430000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 4428, -71, 16510, 0, -180, 0, 0x00460000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, 143, 0, -16491, 0, -180, 0, 0x00480000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -3516, 0, -13872, 0, -180, 0, 0x00480000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -7176, 0, -11253, 0, -180, 0, 0x00480000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -10882, 0, -8696, 0, -180, 0, 0x00480000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -14629, 0, -6281, 0, -180, 0, 0x00480000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -18177, 0, -3530, 0, -180, 0, 0x00480000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -21164, 0, -248, 0, -180, 0, 0x00480000, bhvPoleGrabbing),
		OBJECT(MODEL_NONE, -23516, 0, 3567, 0, -180, 0, 0x00480000, bhvPoleGrabbing),
		TERRAIN(jrb_area_1_collision),
		MACRO_OBJECTS(jrb_area_1_macro_objs),
		SET_BACKGROUND_MUSIC(0x00, SEQ_LEVEL_WATER),
		TERRAIN_TYPE(TERRAIN_GRASS),
		/* Fast64 begin persistent block [area commands] */
		/* Fast64 end persistent block [area commands] */
		OBJECT(MODEL_GOOMBA, -11000, 0, -12700, 0, -70, 0, 0x00000000, bhvGoomba),
		OBJECT(MODEL_GOOMBA, -15800, 0, -10700, 0, 120, 0, 0x00000000, bhvGoomba),
		OBJECT(MODEL_GOOMBA, -10200, 0, -7800, 0, -120, 0, 0x00000000, bhvGoomba),
		OBJECT(MODEL_GOOMBA, -18000, 0, 8800, 0, 150, 0, 0x00000000, bhvGoomba),
		OBJECT(MODEL_GOOMBA, 12000, 0, 10000, 0, -180, 0, 0x00000000, bhvGoomba),
	END_AREA(),
	FREE_LEVEL_POOL(),
	MARIO_POS(0x01, 30, -13300, 100, -11900),
	CALL(0, lvl_init_or_update),
	CALL_LOOP(1, lvl_init_or_update),
	CLEAR_LEVEL(),
	SLEEP_BEFORE_EXIT(1),
	EXIT(),
};