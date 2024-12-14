import string

class MyTemplate(string.Template):
    delimiter = "<>"

class CodeTemplate:
    def __init__(self, template_text):
        metadata, template = template_text.split("\n####\n", 1)

        name, metadata = metadata.split("\n", 1)
        self.name = name = name[2:]

        self.separators = {}
        for metadata in metadata.split("\n"):
            _, parameter, separator = (metadata.split(" ", 2)+["",])[:3]

            if separator:
                self.separators[parameter] = separator.replace("\\n", "\n")
            else:
                self.separators[parameter] = ""

        self.values = {parameter:[] for parameter in self.separators}

        self.template = MyTemplate(template)
        self.template.substitute(self.separators)

    def add(self, **kwargs) -> 'CodeTemplate':
        for parameter_name, value in kwargs.items():
            if parameter_name not in self.values:
                raise Exception(f"Parameter {parameter_name} not in CodeTemplate {self.name}")
            self.values[parameter_name].append(str(value))
        
        return self
    
    def render(self) -> str:
        return self.template.substitute({
            parameter: self.separators[parameter].join(values)
            for parameter, values in self.values.items()
        })


class CodeTemplates:
    '''Loads all templates from a template file
    Templates are separated by a line with 8 '#', '########'
    followed by the template name and all the parameters with their separators
    follwed by the templated

    ex:
    ########
    # template_1
    # arg1 ,
    # arg2 \n
    # arg3
    ####
    '''
    def __init__(self, file_path):
        with open(file_path, "r") as f:
            templates_text = [template_text.strip() for template_text in f.read().split("########")]

        if templates_text[0] == "":
            templates_text = templates_text[1:]

        self.templates = {}
        for template_text in templates_text:
            template = CodeTemplate(template_text)
            self.templates[template.name] = template_text

    def get(self, template_name) -> CodeTemplate:
        return CodeTemplate(self.templates[template_name])

    def template(self, template_name) -> CodeTemplate:
        return self.get(template_name)
    def __getitem__(self, template_name) -> CodeTemplate:
        return self.get(template_name)


if __name__ == "__main__":
    templates = CodeTemplates("cool/code_generation/cgen.stg")

    print(templates.templates)
    t1=templates["program"]
    print(t1.render())