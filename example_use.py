from autoswitcher_class import Autoswitcher as ASW
from souddevice import query_devices

# variables (configure those according to your needs)
ulist: list[str] = [f'User_0{i}' for i in range(3)]
dlist: list[int] = [i for i in range(3)]
sspeak: list[str] = [f'Scene_Speaker_0{i}' for i in range(3)]
sedito: list[str] = [f'Scene_Edito_0{i}' for i in range(3)]
sfill: list[str] = [f'Scene_Fill_0{i}' for i in range(3)]
creds: dict = {'host': "", 'port': 0, 'password': ""}
tsh: int = 5

# call for display of inputs and outputs
print(query_devices())

# calling for interface and switch
my_autoswitcher = ASW(
    users=ulist,
    devices=dlist,
    scene_speaker=sspeak,
    scene_edito=sedito,
    scene_fill=sfill,
    obs_creditentials=creds,
    threshold=tsh
).switch()
