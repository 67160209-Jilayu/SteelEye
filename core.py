import os
import datetime
import zipfile
import json

class MainSystem:
    def __init__(self , model , precision : float):
        self.model = model
        self.precision = precision
        self.input_basket = "image_basket/input"
        self.output_basket = "image_basket/output"
        self.package = "package/"
        self.allow_file_type = [".png" , ".jpg" , ".jpeg"]
        self.steel_type = {
            "0" : "เหล็กกล่อง",
            "1" : "เหล็กเส้น"
        }
        self.history : dict[str , dict[str , dict]]= {}

    def predict_all_and_save(self , list_image : list[str]) -> list[str]:
        images_path : list[str] = []
        for i in list_image:
            images_path.append(self.input_basket + "/" + i)

        history : dict[str , dict]= {}
        results_list = self.model.predict(source=images_path ,conf=self.precision)

        for i , result in enumerate(results_list):
            boxes = result.boxes
            avg_confident = []
            # ใช้ basename แทน hardcode [19:] เพื่อรองรับ path ยาวทุกรูปแบบ
            image_name = os.path.basename(images_path[i])
            history.update({image_name: {}})

            for box in boxes:
                name = self.steel_type[result.names[int(box.cls[0].item())]]
                avg_confident.append(box.conf[0].item())

                if not history[image_name].get(name) : history[image_name].update({name : 1})
                else: history[image_name][name] += 1

            if sum(avg_confident) > 0: avg_confident = sum(avg_confident) / len(avg_confident)
            else: avg_confident = 0
            history[image_name].update({"avg_confident" : avg_confident})
            result.save(self.output_basket + "/" + image_name)


        self.history.update({datetime.datetime.now().strftime("%c") : history})
        return list(history.keys())


    def get_all_history(self): return self.history

    def get_history_date(self): return list(self.history.keys())

    def get_some_history(self , date : str): return self.history[date]

    def recall_history_image(self , date : str) -> list[str]: return list(self.history[date].keys())


    def packing_output_by_date(self , date : str) -> str:
        if date == "newest": select = max(list(self.history.keys()))
        elif date == "oldest": select = min(list(self.history.keys()))
        else: select = date

        select_image = [self.output_basket + "/" + i for i in self.history[select].keys()]

        with open(select + ".txt" , "w") as f:
            json.dump(self.history[select] , f , indent=4)

        with zipfile.ZipFile(select + ".zip" , "w") as zipf:
            zipf.write(select + ".txt")
            for image in select_image:
                zipf.write(image)

        os.replace(select + ".zip" , self.package + select + ".zip")
        os.remove(select + ".txt")
        return select + ".zip"


class UniqueRuntimeSystem:
    def __init__(self , main_system : MainSystem , runtime_id : str):
        self.runtime = main_system
        self.runtime_id = runtime_id
        self.input_basket_tracker : list[str] = []
        self.output_basket_tracker :  list[str] = []
        self.packing_basket_tracker : list[str] = []


    def receive_image(self, image_list : list[str]): self.input_basket_tracker.extend(image_list)

    def predict(self):
        self.output_basket_tracker.extend(self.runtime.predict_all_and_save(self.input_basket_tracker))
        self.input_basket_tracker.clear()

    def redo_predict(self , date : str):
        if self.runtime.history.get(date):
            to_redo = list(self.runtime.history[date].keys())
            self.output_basket_tracker.extend(self.runtime.predict_all_and_save(to_redo))


    def packing_by_date(self , date="newest"):
        self.packing_basket_tracker.append(self.runtime.packing_output_by_date(date))

    def get_input_basket(self): return self.input_basket_tracker

    def get_output_basket(self): return self.output_basket_tracker

    def get_all_history(self): return self.runtime.get_all_history()

    def get_history_date(self): return list(self.runtime.get_history_date())

    def get_some_history(self , date : str): return self.runtime.get_some_history(date)

    def get_newest_history(self): return self.runtime.get_some_history(max(self.runtime.get_history_date()))

    def recall_history_image(self , date : str) -> list[str]: return self.runtime.recall_history_image(date)

    def recall_newest_history_image(self): return self.runtime.recall_history_image(max(self.runtime.get_history_date()))

    def get_packing_basket(self): return self.packing_basket_tracker

    def save_runtime(self):
        with open("user_history.json" , "r") as f:
            user_history : dict = json.load(f)

        with open("user_history.json" , "w") as f:
            to_save = {self.runtime_id : {"input_basket" : self.input_basket_tracker ,
                                          "output_basket" : self.output_basket_tracker ,
                                          "packing_basket" : self.packing_basket_tracker ,
                                          "history" : self.runtime.get_all_history() ,
                                          "precision" : self.runtime.precision}}
            user_history.update(to_save)
            json.dump(user_history , f , indent=4)

    def reload_runtime(self , runtime_id : str):
        with open("user_history.json" , "r") as f:
            user_history : dict = json.load(f)

        if user_history.get(runtime_id):
            self.input_basket_tracker: list[str] = user_history[runtime_id]["input_basket"]
            self.output_basket_tracker: list[str] = user_history[runtime_id]["output_basket"]
            self.packing_basket_tracker: list[str] = user_history[runtime_id]["packing_basket"]

            self.runtime.history = user_history[runtime_id]["history"]
            self.runtime.precision = user_history[runtime_id]["precision"]