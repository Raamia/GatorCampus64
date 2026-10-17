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
		OBJECT(MODEL_YELLOW_COIN, 1150, 60, 1520, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_NONE, -2110, 0, -1880, 0, -180, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, -730, 0, 2260, 0, 90, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, 810, 0, 2160, 0, -180, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, -15, 0, -1980, 0, -180, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, -15, 0, -1130, 0, 90, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, -10, 0, -3200, 0, 90, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, 2710, 0, 2540, 0, 90, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_YELLOW_COIN, -180, 128, 1931, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, 160, 128, 1931, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, -180, 246, 1727, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, 160, 246, 1727, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, -180, 364, 1522, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, 160, 364, 1522, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, -180, 483, 1317, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, 160, 483, 1317, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, -180, 601, 1112, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, 160, 601, 1112, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_NONE, -10, 0, 660, 0, 90, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, -3030, 0, 1060, 0, -180, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, -10, 600, 530, 0, 90, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, 1070, 600, 1170, 0, 90, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, -10, 600, -3200, 0, 90, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, 3130, 600, -1940, 0, -180, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_YELLOW_COIN, -2910, 960, -2630, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, -1674, 960, -1750, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, -628, 960, -2630, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, 598, 960, -1750, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, 1644, 960, -1750, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, 2690, 960, -1750, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, 2885, 960, -2630, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_NONE, 1030, 600, -1980, 0, -180, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, -1060, 600, -1980, 0, -180, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_YELLOW_COIN, -2540, 660, 1850, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, -2370, 660, 1850, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, -2200, 660, 1850, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_NONE, 3710, 1200, 760, 0, -180, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, 2077, 1200, -1740, 0, -180, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, -3130, 1200, 1460, 0, -180, 0, 0x00020000, bhvCoinFormation),
		OBJECT(MODEL_NONE, -15, 1200, -1980, 0, -180, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_YELLOW_COIN, -1674, 1560, -1750, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, -628, 1560, -2630, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, 598, 1560, -1750, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_NONE, -10, 1200, 2240, 0, 90, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, -3290, 1200, 1460, 0, -180, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, 3310, 1800, 1560, 0, -180, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, 10, 1800, -1840, 0, -180, 0, 0x00020000, bhvCoinFormation),
		OBJECT(MODEL_NONE, 1710, 1800, -640, 0, 90, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, -1790, 1800, -540, 0, 90, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, -390, 1800, 500, 0, 90, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, -10, 1800, 2460, 0, 90, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, -3440, 1800, 1560, 0, -180, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, -10, 2400, 960, 0, 90, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, -390, 3000, 520, 0, 90, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, -2370, 3000, 1910, 0, -180, 0, 0x00000000, bhvCoinFormation),
		OBJECT(MODEL_NONE, 0, 3000, 2000, 0, 90, 0, 0x00000000, bhvCoinFormation),
		MARIO_POS(0x01, -180, 0, 100, 2320),
		OBJECT(MODEL_NONE, 0, 100, 2320, 0, -180, 0, 0x000A0000, bhvSpinAirborneWarp),
		OBJECT_WITH_ACTS(MODEL_GOOMBA, -15, 0, -2420, 0, 90, 0, 0x00000000, bhvGoomba, ACT_1 | ACT_2 | ACT_4 | ACT_5 | ACT_6),
		OBJECT(MODEL_GOOMBA, 2710, 0, 1660, 0, 90, 0, 0x00000000, bhvGoomba),
		OBJECT_WITH_ACTS(MODEL_GOOMBA, 2077, 600, -1540, 0, 90, 0, 0x00000000, bhvGoomba, ACT_1 | ACT_2 | ACT_4 | ACT_5 | ACT_6),
		OBJECT_WITH_ACTS(MODEL_GOOMBA, -1060, 1200, -2420, 0, 90, 0, 0x00000000, bhvGoomba, ACT_1 | ACT_2 | ACT_4 | ACT_5 | ACT_6),
		OBJECT(MODEL_HEART, -810, 100, 1890, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_HEART, -15, 700, -2420, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_HEART, -1690, 1900, -1440, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_HEART, -2370, 3100, 1480, 0, -180, 0, 0x00000000, bhvRecoveryHeart),
		OBJECT(MODEL_YELLOW_COIN, 1630, 360, 2582, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, 1630, 960, 2582, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, 1630, 1560, 2582, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, 1630, 2160, 2582, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, 1630, 2760, 2582, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, 2005, 360, -3159, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, 2005, 960, -3159, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, 2005, 1560, -3159, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, -2010, 360, -3167, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, -2010, 960, -3167, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, -2010, 1560, -3167, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, -1660, 360, 2582, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, -1660, 960, 2582, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, -1660, 1560, 2582, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, -1660, 2160, 2582, 0, -180, 0, 0x00000000, bhvYellowCoin),
		OBJECT(MODEL_YELLOW_COIN, -1660, 2760, 2582, 0, -180, 0, 0x00000000, bhvYellowCoin),
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