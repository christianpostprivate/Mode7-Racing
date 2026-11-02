# TODO grab and populate the SCENES dict automatically
from src.scenes.title_screen import TitleScreen
from src.scenes.asset_loader import AssetLoader
from src.scenes.course_select import CourseSelect
from src.scenes.kart_select import KartSelect
from src.scenes.race import Race

SCENES = {
    "AssetLoader": AssetLoader,
    "TitleScreen": TitleScreen,
    "CourseSelect": CourseSelect,
    "KartSelect": KartSelect,
    "Race": Race,
}